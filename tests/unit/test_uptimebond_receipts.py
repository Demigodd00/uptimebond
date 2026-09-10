"""A canceled or pending successful leader is not a committed observation."""

import pytest

from scripts.uptimebond_acceptance import child_execution_facts


@pytest.mark.parametrize(
    "status,leader_result,committed",
    [
        ("FINALIZED", "SUCCESS", True),
        ("FINALIZED", "ERROR", False),
        ("CANCELED", "SUCCESS", False),
        ("COMMITTING", "SUCCESS", False),
        ("ACCEPTED", "SUCCESS", False),
        ("UNDETERMINED", "SUCCESS", False),
    ],
)
def test_leader_success_requires_finality(status, leader_result, committed):
    receipt = {
        "status": status,
        "consensus_data": {"leader_receipt": [{"execution_result": leader_result}]},
    }
    assert child_execution_facts(receipt) == {
        "child_status_at_timeout": status,
        "leader_execution_succeeded": leader_result == "SUCCESS",
        "child_committed_successfully": committed,
    }


def test_missing_receipt_never_counts_as_success():
    assert child_execution_facts(None) == {
        "child_status_at_timeout": "NOT_FOUND",
        "leader_execution_succeeded": False,
        "child_committed_successfully": False,
    }
