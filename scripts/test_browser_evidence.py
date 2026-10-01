"""Exercise the portable evidence package without app or cloud credentials."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


def load_tests(_loader, _tests, _pattern):
    tests = unittest.TestLoader().discover(str(ROOT / "browser-evidence/tests"), pattern="test_*.py")
    tests.addTests(unittest.TestLoader().loadTestsFromTestCase(ReporterTests))
    return tests


class ReporterTests(unittest.TestCase):
    def test_reporter_behavior(self):
        files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "browser-evidence/tests").glob("*.test.mjs"))
        result = subprocess.run(["node", "--test", *files], cwd=ROOT,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
