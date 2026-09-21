from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parent.parent / "empirical-prompt-tuning/scripts/ept_score.py"
spec = importlib.util.spec_from_file_location("ept_score", path)
ept = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ept)


def iteration(result="ok"):
    return {"scenarios": [{"name": n, "requirements": [{"critical": True, "result": result}, {"critical": False, "result": "ok"}, {"critical": False, "result": "ok"}], "tool_uses": 4, "duration_ms": 10, "retries": 0, "new_unclear": 0} for n in ("A", "B")]}


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

    def test_accuracy_regression_does_not_converge(self):
        before = ept.iteration_summary(iteration())
        after = dict(before, accuracy=70)
        self.assertFalse(ept.transition_clear(before, after)[1])


if __name__ == "__main__":
    unittest.main()
