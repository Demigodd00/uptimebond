"""Full-consensus UptimeBond smoke test for GenLayer StudioNet.

This test deploys a temporary contract and takes one small test-GEN bond through
readiness, acceptance, two independent endpoint observations, and settlement.
It is intentionally not part of the default local suite because it performs
real StudioNet writes and waits through the contract's fixed time windows.
"""

import os
import time

from gltest import get_accounts, get_contract_factory
from gltest.assertions import tx_execution_succeeded

STAKE = 10**15
ENDPOINT = os.environ.get(
    "UPTIMEBOND_TEST_ENDPOINT",
    "https://uptimebond-psi.vercel.app/api/demo-health",
)
PROOF_TOKEN = os.environ.get("UPTIMEBOND_TEST_TOKEN", "uptimebond-demo-v1")


def _wait_until(unix_ts: int) -> None:
    while time.time() < unix_ts + 2:
        time.sleep(min(10, max(1, unix_ts + 2 - int(time.time()))))


def _assert_rejected(tx) -> None:
    assert not tx_execution_succeeded(tx)


def test_complete_met_bond_on_studionet():
    factory = get_contract_factory("UptimeBond")
    provider_contract = factory.deploy(args=[])
    provider, beneficiary, observer = get_accounts()[:3]
    beneficiary_contract = provider_contract.connect(beneficiary)
    observer_contract = provider_contract.connect(observer)

    now = int(time.time())
    accept_by = now + 300
    starts_at = accept_by + 60
    interval_secs = 60
    slot_count = 2

    create_tx = provider_contract.create_bond(
        args=[
            "UptimeBond StudioNet fixture",
            ENDPOINT,
            beneficiary.address,
            200,
            PROOF_TOKEN,
            accept_by,
            starts_at,
            interval_secs,
            slot_count,
            2,
            0,
        ]
    ).transact(value=STAKE)
    assert tx_execution_succeeded(create_tx)

    listing = provider_contract.list_bonds(args=[0, 25]).call()
    bond_id = listing["items"][-1]["id"]
    offered = provider_contract.get_bond(args=[bond_id]).call()
    assert offered["status"] == "OFFERED"
    assert offered["bond_atto"] == str(STAKE)
    assert offered["beneficiary"].lower() == beneficiary.address.lower()

    wrong_ready = observer_contract.verify_readiness(args=[bond_id]).transact()
    _assert_rejected(wrong_ready)

    ready_tx = provider_contract.verify_readiness(args=[bond_id]).transact()
    assert tx_execution_succeeded(ready_tx)
    ready = provider_contract.get_bond(args=[bond_id]).call()
    assert ready["status"] == "READY"
    assert ready["readiness"]["exists"] is True
    assert ready["readiness"]["http_status"] == "200"
    assert len(ready["readiness"]["body_digest"]) == 64

    accept_tx = beneficiary_contract.accept_bond(args=[bond_id]).transact()
    assert tx_execution_succeeded(accept_tx)
    assert provider_contract.get_bond(args=[bond_id]).call()["status"] == "ACTIVE"

    early_observation = observer_contract.record_observation(args=[bond_id]).transact()
    _assert_rejected(early_observation)

    _wait_until(starts_at)
    first_tx = observer_contract.record_observation(args=[bond_id]).transact()
    assert tx_execution_succeeded(first_tx)

    _wait_until(starts_at + interval_secs)
    second_tx = beneficiary_contract.record_observation(args=[bond_id]).transact()
    assert tx_execution_succeeded(second_tx)

    duplicate_tx = observer_contract.record_observation(args=[bond_id]).transact()
    _assert_rejected(duplicate_tx)

    observations = provider_contract.get_observations(args=[bond_id]).call()
    assert observations["total"] == "2"
    assert [item["slot_index"] for item in observations["items"]] == ["0", "1"]
    assert all(item["result"] == "PASS" for item in observations["items"])
    assert all(len(item["body_digest"]) == 64 for item in observations["items"])

    _wait_until(starts_at + interval_secs * slot_count)
    finalize_tx = observer_contract.finalize_bond(args=[bond_id]).transact()
    assert tx_execution_succeeded(finalize_tx)

    settled = provider_contract.get_bond(args=[bond_id]).call()
    assert settled["status"] == "MET"
    assert settled["result"] == "SLA_MET"
    assert settled["payout_recipient"].lower() == provider.address.lower()
    assert settled["payout_atto"] == str(STAKE)
    stats = provider_contract.get_stats().call()
    assert stats["total_created"] == "1"
    assert stats["total_finalized"] == "1"
    assert stats["total_met"] == "1"
    assert stats["total_locked_atto"] == "0"
    assert stats["admin_controls"] is False
