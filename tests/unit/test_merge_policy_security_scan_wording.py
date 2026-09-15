import re
from pathlib import Path


def test_gate_2_states_security_jobs_are_completion_gates() -> None:
    policy_path = Path(__file__).resolve().parents[2] / "MERGE_POLICY.md"
    policy = policy_path.read_text()

    assert re.search(
        r"gate 2 requires these security scan jobs \(check-runs\) to .*run and complete",
        policy,
        re.IGNORECASE,
    )
    assert "It is not a findings gate" in policy
