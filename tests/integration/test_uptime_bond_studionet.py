"""Full-consensus, real-GenVM smoke test of autonomous check dispatch.

Deploys a temporary StudioNet contract; never changes the canonical address.
Run explicitly with gltest tests/integration/test_uptime_bond_studionet.py -v -s.
"""
import os
import time

from gltest import get_accounts, get_contract_factory
from gltest.assertions import tx_execution_succeeded

STAKE = 10**15
ENDPOINT = os.environ.get("UPTIMEBOND_TEST_ENDPOINT", "https://uptimebond-psi.vercel.app/api/demo-health")
PROOF_TOKEN = os.environ.get("UPTIMEBOND_TEST_TOKEN", "uptimebond-demo-v1")


def test_complete_met_bond_on_studionet():
    factory = get_contract_factory("UptimeBond")
    contract = factory.deploy(args=[])
    provider, beneficiary, observer = get_accounts()[:3]
    print(f"temporary_contract={contract.address}", flush=True)
    beneficiary_contract = contract.connect(beneficiary)
    observer_contract = contract.connect(observer)

    receipt = contract.create_bond(args=[
        "UptimeBond autonomous consensus smoke", ENDPOINT, beneficiary.address,
        200, PROOF_TOKEN, int(time.time()) + 900, 2, 0,
    ]).transact(value=STAKE)
    assert tx_execution_succeeded(receipt)
    assert tx_execution_succeeded(contract.verify_readiness(args=["ub-1"]).transact())
    acceptance = beneficiary_contract.accept_bond(args=["ub-1"]).transact()
    assert tx_execution_succeeded(acceptance)

    # Never call record_observation successfully from any wallet.
    rejected = observer_contract.record_observation(args=["ub-1", 0]).transact()
    assert not tx_execution_succeeded(rejected)
    deadline = time.monotonic() + 660
    while time.monotonic() < deadline:
        state = contract.get_bond(args=["ub-1"]).call()
        print(f"autonomous status={state['status']} observed={state['observed_count']}", flush=True)
        if state["status"] != "ACTIVE":
            break
        time.sleep(10)
    assert state["status"] == "MET", state
    assert state["result"] == "ALL_REQUIRED_CHECKS_MET"
    assert state["payout_recipient"].lower() == provider.address.lower()
    assert state["payout_atto"] == str(STAKE)
    observations = contract.get_observations(args=["ub-1"]).call()["items"]
    assert len(observations) == 2
    assert [item["slot_index"] for item in observations] == ["0", "1"]
    assert all(item["result"] == "PASS" and len(item["body_digest"]) == 64 for item in observations)
    assert all(int(item["deadline_unix"]) - int(item["scheduled_at_unix"]) == 300 for item in observations)
    stats = contract.get_stats().call()
    assert stats["total_locked_atto"] == "0"
    assert stats["total_returned_to_providers_atto"] == str(STAKE)
    assert stats["sampling_policy"] == "AUTONOMOUS_FINALIZED_SELF_CALLS"
    assert stats["missing_evidence_payout"] == "BENEFICIARY"
