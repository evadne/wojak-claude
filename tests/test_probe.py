"""Guard against counting infrastructure failures as model observations."""

import importlib.util
import json
from pathlib import Path
import unittest
from collections import Counter

spec = importlib.util.spec_from_file_location("probe", Path(__file__).resolve().parents[1] / "scripts/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ResultIntegrity(unittest.TestCase):
    def result(self, **overrides):
        value = {"type": "result", "subtype": "success", "is_error": False,
                 "modelUsage": {"claude-fable-5-2": {}}, "result": '{"observed":true}'}
        value.update(overrides)
        return json.dumps(value)

    def test_auth_error_is_not_a_model_failure_even_with_success_subtype(self):
        response = probe.final_result(self.result(is_error=True, result="Authentication failed"), 1, "claude-fable-5-2")
        self.assertEqual(response["status"], "infrastructure_error")

    def test_silent_model_change_invalidates_the_observation(self):
        response = probe.final_result(self.result(modelUsage={"claude-opus-5-5": {}}), 0, "claude-fable-5-2")
        self.assertEqual(response["status"], "invalid_model")

    def test_truncated_stream_is_not_a_completed_observation(self):
        response = probe.final_result('{"type":"assistant"}\n', 0, "claude-fable-5-2")
        self.assertEqual(response["status"], "infrastructure_error")

    def test_valid_answer_preserves_the_full_result(self):
        response = probe.final_result(self.result(), 0, "claude-fable-5-2")
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["parsed_answer"], {"observed": True})

    def test_shuffling_preserves_each_planned_observation(self):
        conditions = [{"id": "baseline"}, {"id": "fidelity"}]
        jobs = probe.schedule_jobs(conditions, 2, seed=20261114)
        expected = Counter((c["id"], n) for c in conditions for n in (1, 2))
        self.assertEqual(Counter((c["id"], n) for c, n in jobs), expected)
        self.assertEqual(jobs, probe.schedule_jobs(conditions, 2, seed=20261114))


if __name__ == "__main__":
    unittest.main()
