from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parent.parent / "empirical-prompt-tuning/scripts/ept_score.py"
spec = importlib.util.spec_from_file_location("ept_score", path)
ept = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ept)


def iteration(result="ok"):
    return {"scenarios": [{"name": n, "requirements": [{"text": "No false success", "critical": True, "result": result}, {"text": "Write output", "critical": False, "result": "ok"}, {"text": "Explain changes", "critical": False, "result": "ok"}], "tool_uses": 4, "duration_ms": 10, "retries": 0, "new_unclear": 0} for n in ("A", "B")]}


def holdout():
    return dict(iteration()["scenarios"][0], name="C")


def render(data):
    output = StringIO()
    with patch.object(ept, "read_input", return_value=data), redirect_stdout(output):
        ept.main()
    return output.getvalue()


class ScoreTests(unittest.TestCase):
    def test_stable_failure_does_not_converge(self):
        summary = ept.iteration_summary(iteration("ng"))
        self.assertFalse(ept.transition_clear(summary, summary)[1])

    def test_valid_stable_success(self):
        data = {"iterations": [iteration(), iteration(), iteration()]}
        ept.validate_input(data)
        summary = ept.iteration_summary(data["iterations"][0])
        self.assertTrue(ept.transition_clear(summary, summary)[1])

    def test_missing_metrics_empty_and_single_scenario_rejected(self):
        missing = iteration()
        del missing["scenarios"][0]["duration_ms"]
        for data in ({"iterations": []}, {"iterations": [{"scenarios": []}]}, {"iterations": [missing]}, {"iterations": [{"scenarios": [iteration()["scenarios"][0]]}]}):
            with self.assertRaises(ValueError):
                ept.validate_input(data)

    def test_changed_requirements_rejected(self):
        before = iteration()
        after = deepcopy(before)
        after["scenarios"][0]["requirements"][1]["critical"] = True
        with self.assertRaises(ValueError):
            ept.validate_input({"iterations": [before, after]})

    def test_changed_requirement_text_rejected_even_with_same_flags(self):
        before = iteration()
        after = deepcopy(before)
        after["scenarios"][0]["requirements"][1]["text"] = "A different goal"
        with self.assertRaises(ValueError):
            ept.validate_input({"iterations": [before, after]})

    def test_missing_blank_and_duplicate_requirement_identity_rejected(self):
        for text in (None, "", "  ", 12, "No false success", " No false success "):
            with self.subTest(text=text):
                current = iteration()
                current["scenarios"][0]["requirements"][1]["text"] = text
                with self.assertRaises(ValueError):
                    ept.validate_input({"iterations": [current]})
        current = iteration()
        del current["scenarios"][0]["requirements"][0]["text"]
        with self.assertRaises(ValueError):
            ept.validate_input({"iterations": [current]})

    def test_holdout_is_separate_and_combined_with_convergence(self):
        data = {"iterations": [iteration(), iteration(), iteration()], "holdout": holdout()}
        ept.validate_input(data)
        output = render(data)
        self.assertIn("| 連続クリア回数 | 2/2 |", output)
        self.assertIn("| hold-out | ○ |", output)
        self.assertIn("| 総合判定 | ○ |", output)
        data["holdout"]["requirements"][1]["result"] = "ng"
        output = render(data)
        self.assertIn("| 連続クリア回数 | 2/2 |", output)
        self.assertIn("| hold-out | × |", output)
        self.assertIn("| 総合判定 | × |", output)

    def test_holdout_does_not_hide_insufficient_iterations(self):
        output = render({"iterations": [iteration()], "holdout": holdout()})
        self.assertIn("## hold-out 判定", output)
        self.assertIn("| hold-out | ○ |", output)
        self.assertIn("| 総合判定 | × |", output)

    def test_holdout_drop_boundary(self):
        # 5 requirements: one partial -> 90%; 4 requirements: one ng -> 75%.
        baseline = iteration()
        for scenario in baseline["scenarios"]:
            scenario["requirements"] += [
                {"text": "Extra output", "critical": False, "result": "partial"},
                {"text": "Preserve input", "critical": False, "result": "ok"},
            ]
        scenario = holdout()
        scenario["requirements"].append({"text": "Extra output", "critical": False, "result": "ng"})
        ept.validate_input({"iterations": [baseline], "holdout": scenario})
        summary = ept.holdout_summary(baseline, scenario)
        self.assertAlmostEqual(summary["drop"], 15.0)
        self.assertFalse(summary["passed"])
        scenario["requirements"][-1]["result"] = "partial"
        self.assertTrue(ept.holdout_summary(baseline, scenario)["passed"])

    def test_holdout_critical_failure_rejected_even_with_small_drop(self):
        scenario = holdout()
        scenario["requirements"][0]["result"] = "partial"
        scenario["requirements"].append({"text": "Extra output", "critical": False, "result": "ok"})
        summary = ept.holdout_summary(iteration(), scenario)
        self.assertLess(summary["drop"], 15)
        self.assertFalse(summary["passed"])

    def test_invalid_or_reused_holdout_rejected(self):
        missing = holdout()
        del missing["duration_ms"]
        for scenario in (None, [], {}, missing, dict(holdout(), name=" A ")):
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                ept.validate_input({"iterations": [iteration()], "holdout": scenario})

    def test_documented_json_examples_validate(self):
        package = path.parent.parent
        for document in (package / "SKILL.md", package / "references/example-run.md"):
            examples = re.findall(r"```json\n(.*?)\n```", document.read_text(), re.S)
            self.assertTrue(examples)
            for example in examples:
                data = json.loads(example)
                if "iterations" not in data:
                    data["iterations"] = [iteration()]
                ept.validate_input(data)

    def test_accuracy_regression_does_not_converge(self):
        before = ept.iteration_summary(iteration())
        after = dict(before, accuracy=70)
        self.assertFalse(ept.transition_clear(before, after)[1])


if __name__ == "__main__":
    unittest.main()
