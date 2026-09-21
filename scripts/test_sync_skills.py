"""Exercise discovery, drift detection and collision handling in an isolated repo."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("sync-skills.sh")


class SyncSkillsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.root / "scripts/sync-skills.sh")
        source = self.root / "example"
        (source / "agents").mkdir(parents=True)
        (source / "SKILL.md").write_text("---\nname: example\ndescription: Example\n---\nBody\n")
        (source / "agents/openai.yaml").write_text("interface: {}\n")

    def run_sync(self, *args):
        return subprocess.run(["bash", str(self.root / "scripts/sync-skills.sh"), *args], text=True, capture_output=True, timeout=10)

    def test_shared_source_and_claude_projection(self):
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual((self.root / ".agents/skills/example").resolve(), (self.root / "example").resolve())
        self.assertFalse((self.root / ".claude/skills/example/agents").exists())
        self.assertEqual(self.run_sync("--check").returncode, 0)

    def test_check_detects_stale_copy_and_broken_link(self):
        self.run_sync()
        (self.root / "example/SKILL.md").write_text("changed source")
        self.assertNotEqual(self.run_sync("--check").returncode, 0)
        self.run_sync()
        link = self.root / ".agents/skills/example"
        link.unlink()
        link.symlink_to("../../missing")
        self.assertNotEqual(self.run_sync("--check").returncode, 0)
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.run_sync("--check").returncode, 0)

    def test_real_directory_collision_is_preserved(self):
        owned = self.root / ".agents/skills/example"
        owned.mkdir(parents=True)
        (owned / "my-file").write_text("keep me")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual((owned / "my-file").read_text(), "keep me")

    def test_orphan_links_and_invalid_mode(self):
        self.run_sync()
        link = self.root / ".agents/skills/orphan"
        link.symlink_to("../../missing")
        self.assertNotEqual(self.run_sync("--check").returncode, 0)
        self.assertEqual(self.run_sync("--typo").returncode, 2)
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertFalse(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
