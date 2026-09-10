"""Adversarial sampling and settlement tests, including explicit validator replay."""
import hashlib
import itertools
import sys
from datetime import datetime, timezone

import pytest

TEST_NOW_UNIX = 2_000_000_000
BOND = 10**18
TIMEOUT = 300
ENDPOINT = "https://status.example.com/health"
TOKEN = "uptimebond-demo-v1"
UP_BODY = '{"service":"demo","proof":"uptimebond-demo-v1","status":"up"}'


def _addr_hex(address):
    raw = address.as_bytes if hasattr(address, "as_bytes") else address
    return "0x" + raw.hex() if isinstance(raw, bytes) else str(address)


def _warp(vm, unix):
    timestamp = datetime.fromtimestamp(unix, tz=timezone.utc).isoformat()
    vm.warp(timestamp)
    module = sys.modules.get("_contract_uptime_bond")
    if module is not None:
        module.gl.message_raw["datetime"] = timestamp


@pytest.fixture(autouse=True)
def start_clock(direct_vm):
    _warp(direct_vm, TEST_NOW_UNIX)


def _mock(vm, body=UP_BODY, status=200):
    vm.clear_mocks()
    vm.mock_web(r".*status\.example\.com/health.*", {"status": status, "body": body})


def _create(vm, contract, provider, beneficiary, *, amount=BOND, endpoint=ENDPOINT,
            expected_status=200, token=TOKEN, accept_by=TEST_NOW_UNIX + 300,
            slots=3, allowed_failures=0):
    vm.sender = provider
    vm.value = amount
    try:
        return contract.create_bond("Demo API", endpoint, _addr_hex(beneficiary),
                                    expected_status, token, accept_by, slots, allowed_failures)
    finally:
        vm.value = 0


def _activate(vm, contract, bond_id, provider, beneficiary):
    vm.sender = provider
    _mock(vm)
    contract.verify_readiness(bond_id)
    assert vm.run_validator() is True
    vm.sender = beneficiary
    contract.accept_bond(bond_id)


def _self_check(vm, contract, bond_id, index, *, status=200, body=UP_BODY):
    vm.sender = vm._contract_address
    _mock(vm, body, status)
    contract.record_observation(bond_id, index)


def _capture(vm):
    transfers, messages = [], []
    def hook(_vm, request):
        if "EthSend" in request:
            entry = request["EthSend"]
            transfers.append((str(entry["address"]).lower(), int(entry["value"])))
            return {"ok": None}
        if "PostMessage" in request:
            messages.append(request["PostMessage"])
            return {"ok": None}
        return None
    vm._gl_call_hook = hook
    return transfers, messages


def test_create_commits_all_checks_and_liability(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    bond = contract.get_bond(bond_id)
    assert bond["status"] == "OFFERED"
    assert bond["min_observations"] == bond["slot_count"] == "3"
    assert bond["sampling_policy"] == "AUTONOMOUS_FINALIZED_SELF_CALLS"
    assert bond["evidence_risk_bearer"] == "PROVIDER"
    assert bond["can_observe"] is False
    assert contract.get_stats()["total_locked_atto"] == str(BOND)


@pytest.mark.parametrize("endpoint", ["http://example.com/health", "https://localhost/health",
    "https://127.0.0.1/health", "https://user@example.com/health", "https://example..com/health",
    "https://example.com:bad/health", "https://example.com/bad path"])
def test_rejects_invalid_endpoints(endpoint, direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/uptime_bond.py")
    with pytest.raises(Exception, match="health endpoint"):
        _create(direct_vm, contract, direct_alice, direct_bob, endpoint=endpoint)


@pytest.mark.parametrize(("changes", "error"), [({"amount":0}, "bond must"),
    ({"expected_status":99}, "HTTP status"), ({"token":"short"}, "proof token"),
    ({"accept_by":TEST_NOW_UNIX+60}, "acceptance deadline"),
    ({"slots":1}, "slot count"), ({"slots":13}, "slot count"),
    ({"allowed_failures":3}, "allowed failures")])
def test_invalid_terms_fail(changes, error, direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/uptime_bond.py")
    with pytest.raises(Exception, match=error):
        _create(direct_vm, contract, direct_alice, direct_bob, **changes)


def test_participants_and_readiness(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = direct_deploy("contracts/uptime_bond.py")
    with pytest.raises(Exception, match="different wallets"):
        _create(direct_vm, contract, direct_alice, direct_alice)
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="not ready"):
        contract.accept_bond(bond_id)
    with pytest.raises(Exception, match="only the provider"):
        contract.verify_readiness(bond_id)
    direct_vm.sender = direct_alice
    _mock(direct_vm, body="not-the-token")
    with pytest.raises(Exception, match="FAIL_TOKEN"):
        contract.verify_readiness(bond_id)
    _mock(direct_vm)
    contract.verify_readiness(bond_id)
    assert direct_vm.run_validator() is True
    readiness = contract.get_bond(bond_id)["readiness"]
    assert readiness["body_digest"] == hashlib.sha256(UP_BODY.encode()).hexdigest()
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="only the beneficiary"):
        contract.accept_bond(bond_id)


def test_acceptance_commits_attempt_before_child_and_sends_on_finalized(direct_vm, direct_deploy, direct_alice, direct_bob):
    _, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    records = contract.get_observations(bond_id)["items"]
    assert len(records) == 1 and records[0]["result"] == "PENDING"
    assert records[0]["body_digest"] == "" and records[0]["observed_at_unix"] == "0"
    assert records[0]["deadline_unix"] == str(TEST_NOW_UNIX + TIMEOUT)
    assert records[0]["provenance"] == "ON_CHAIN_COMMITTED_ATTEMPT"
    assert len(messages) == 1
    assert messages[0]["on"] == "finalized"


@pytest.mark.parametrize("who", ["provider", "beneficiary", "unrelated"])
@pytest.mark.parametrize("offset", [0, 5, 100, 299])
def test_no_wallet_can_choose_favorable_check_instant(who, offset, direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    _, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    _warp(direct_vm, TEST_NOW_UNIX + offset)
    direct_vm.sender = {"provider":direct_alice, "beneficiary":direct_bob, "unrelated":direct_charlie}[who]
    with pytest.raises(Exception, match="only the contract"):
        contract.record_observation(bond_id, 0)
    assert contract.get_bond(bond_id)["observed_count"] == "0"
    assert len(messages) == 1


def test_protocol_sequence_requires_all_checks_and_refunds_once(direct_vm, direct_deploy, direct_alice, direct_bob):
    transfers, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    for index in range(3):
        _warp(direct_vm, TEST_NOW_UNIX + 10 * (index + 1))
        _self_check(direct_vm, contract, bond_id, index)
        assert direct_vm.run_validator() is True
        assert len(messages) == min(index + 2, 3)
        if index < 2:
            assert contract.get_bond(bond_id)["status"] == "ACTIVE"
            assert transfers == []
    bond = contract.get_bond(bond_id)
    assert bond["status"] == "MET" and bond["result"] == "ALL_REQUIRED_CHECKS_MET"
    assert bond["observed_count"] == bond["slot_count"] == "3"
    assert bond["uptime_bps"] == "10000"
    assert transfers == [(_addr_hex(direct_alice).lower(), BOND)]
    with pytest.raises(Exception, match="only active"):
        contract.finalize_bond(bond_id)
    assert len(transfers) == 1


def test_no_skip_reorder_duplicate_or_uncommitted_check(direct_vm, direct_deploy, direct_alice, direct_bob):
    _, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    direct_vm.sender = direct_vm._contract_address
    for wrong_index in (1, 2, 12, 100):
        with pytest.raises(Exception, match="unordered"):
            contract.record_observation(bond_id, wrong_index)
    _self_check(direct_vm, contract, bond_id, 0, status=503)
    original = contract.get_observations(bond_id)["items"][0]
    with pytest.raises(Exception, match="duplicate"):
        _self_check(direct_vm, contract, bond_id, 0)
    assert contract.get_observations(bond_id)["items"][0] == original
    assert original["result"] == "FAIL_STATUS" and len(messages) == 2


@pytest.mark.parametrize(("status", "body", "expected"), [
    (503, UP_BODY, "FAIL_STATUS"), (200, "no proof", "FAIL_TOKEN"),
    (503, "no proof", "FAIL_STATUS_AND_TOKEN"), (200, "x"*16001, "FAIL_BODY_LIMIT"),
    (200, b"\xff\xfe", "FAIL_TOKEN")])
def test_objective_failures_remain_recorded(status, body, expected, direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    _self_check(direct_vm, contract, bond_id, 0, status=status, body=body)
    assert direct_vm.run_validator() is True
    assert contract.get_observations(bond_id)["items"][0]["result"] == expected
    assert contract.get_bond(bond_id)["failed_count"] == "1"


@pytest.mark.parametrize("passed_first", [0, 1, 2])
@pytest.mark.parametrize("allowed", [0, 1, 2])
def test_missing_check_never_refunds_even_with_favorable_subset(passed_first, allowed, direct_vm, direct_deploy, direct_alice, direct_bob):
    transfers, _ = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob, allowed_failures=allowed)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    for index in range(passed_first):
        _self_check(direct_vm, contract, bond_id, index)
    assert contract.get_bond(bond_id)["uptime_bps"] == str(passed_first * 10000 // 3)
    _warp(direct_vm, TEST_NOW_UNIX + TIMEOUT)
    direct_vm.sender = direct_alice
    contract.finalize_bond(bond_id)
    bond = contract.get_bond(bond_id)
    assert bond["status"] == "UNVERIFIABLE"
    assert bond["payout_recipient"].lower() == _addr_hex(direct_bob).lower()
    assert transfers == [(_addr_hex(direct_bob).lower(), BOND)]
    item = contract.get_observations(bond_id)["items"][-1]
    assert item["result"] == "UNVERIFIABLE_TIMEOUT"
    assert item["observed_at_unix"] == "0" and item["body_digest"] == ""
    assert contract.get_stats()["total_returned_to_providers_atto"] == "0"
    assert contract.get_stats()["total_locked_atto"] == "0"


def test_deadline_cannot_be_extended_and_late_self_call_cannot_rescue_provider(direct_vm, direct_deploy, direct_alice, direct_bob):
    transfers, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    _warp(direct_vm, TEST_NOW_UNIX + TIMEOUT - 1)
    with pytest.raises(Exception, match="within its evidence deadline"):
        contract.finalize_bond(bond_id)
    _warp(direct_vm, TEST_NOW_UNIX + TIMEOUT)
    _self_check(direct_vm, contract, bond_id, 0)
    assert contract.get_bond(bond_id)["status"] == "UNVERIFIABLE"
    assert transfers == [(_addr_hex(direct_bob).lower(), BOND)]
    assert len(messages) == 1


@pytest.mark.parametrize("vary_field", ["bytes", "status", "token"])
def test_disagreement_rolls_back_child_but_not_parent_obligation(vary_field, direct_vm, direct_deploy, direct_alice, direct_bob):
    transfers, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    snapshot = direct_vm.snapshot()
    _self_check(direct_vm, contract, bond_id, 0)
    if vary_field == "bytes":
        _mock(direct_vm, UP_BODY + " ")
    elif vary_field == "status":
        _mock(direct_vm, status=503)
    else:
        _mock(direct_vm, body="proof removed")
    assert direct_vm.run_validator() is False
    # Model failed consensus: roll back only the child and its emitted messages.
    direct_vm.revert(snapshot)
    del messages[1:]
    assert contract.get_observations(bond_id)["items"][0]["result"] == "PENDING"
    assert contract.get_bond(bond_id)["observed_count"] == "0"
    _warp(direct_vm, TEST_NOW_UNIX + TIMEOUT)
    direct_vm.sender = direct_alice
    contract.finalize_bond(bond_id)
    assert transfers == [(_addr_hex(direct_bob).lower(), BOND)] and len(messages) == 1


def test_transport_errors_cannot_favor_provider(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    transfers, _ = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob, allowed_failures=2)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    module = sys.modules["_contract_uptime_bond"]
    def unavailable(*args, **kwargs):
        raise TimeoutError("variable transport diagnostic")
    monkeypatch.setattr(module.gl.nondet.web, "get", unavailable)
    direct_vm.sender = direct_vm._contract_address
    contract.record_observation(bond_id, 0)
    assert direct_vm.run_validator() is True
    assert contract.get_bond(bond_id)["status"] == "UNVERIFIABLE"
    assert contract.get_observations(bond_id)["items"][0]["result"] == "UNVERIFIABLE_FETCH"
    assert transfers == [(_addr_hex(direct_bob).lower(), BOND)]


@pytest.mark.parametrize("outcomes", list(itertools.product([200, 503], repeat=3)))
@pytest.mark.parametrize("allowed", [0, 1, 2])
def test_every_failure_budget_has_exact_conservative_payout(outcomes, allowed, direct_vm, direct_deploy, direct_alice, direct_bob):
    transfers, _ = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob, allowed_failures=allowed)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    for index, status in enumerate(outcomes):
        _self_check(direct_vm, contract, bond_id, index, status=status)
    failed = outcomes.count(503)
    recipient = direct_bob if failed > allowed else direct_alice
    assert transfers == [(_addr_hex(recipient).lower(), BOND)]
    assert contract.get_bond(bond_id)["status"] == ("BREACHED" if failed > allowed else "MET")
    stats = contract.get_stats()
    assert stats["total_locked_atto"] == "0"
    assert int(stats["total_returned_to_providers_atto"]) + int(stats["total_paid_to_beneficiaries_atto"]) == BOND


@pytest.mark.parametrize(("outcomes", "suppressed"), [
    (outcomes, index) for outcomes in itertools.product([200, 503], repeat=3)
    for index, status in enumerate(outcomes) if status == 503
])
@pytest.mark.parametrize("allowed", [0, 1, 2])
def test_suppressing_any_failure_never_increases_provider_payout(outcomes, suppressed, allowed, direct_vm, direct_deploy, direct_alice, direct_bob):
    transfers, messages = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob, allowed_failures=allowed)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    snapshot = direct_vm.snapshot()
    for index, status in enumerate(outcomes):
        _self_check(direct_vm, contract, bond_id, index, status=status)
    honest_refund = int(contract.get_stats()["total_returned_to_providers_atto"])

    direct_vm.revert(snapshot)
    transfers.clear()
    del messages[1:]
    for index in range(suppressed):
        _self_check(direct_vm, contract, bond_id, index, status=outcomes[index])
    # The unfavorable child is dropped, reverted, or cannot reach consensus.
    _warp(direct_vm, TEST_NOW_UNIX + TIMEOUT)
    direct_vm.sender = direct_alice
    contract.finalize_bond(bond_id)
    suppressed_refund = int(contract.get_stats()["total_returned_to_providers_atto"])
    assert suppressed_refund == 0 and suppressed_refund <= honest_refund
    assert transfers == [(_addr_hex(direct_bob).lower(), BOND)]
    assert contract.get_stats()["total_locked_atto"] == "0"


def test_only_unaccepted_offers_can_refund_or_cancel(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    transfers, _ = _capture(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    first = _create(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="only the provider"):
        contract.cancel_offer(first)
    direct_vm.sender = direct_alice
    contract.cancel_offer(first)
    second = _create(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    contract.decline_bond(second)
    third = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, third, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="cannot be cancelled"):
        contract.cancel_offer(third)
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="no longer be declined"):
        contract.decline_bond(third)
    with pytest.raises(Exception, match="unaccepted"):
        contract.expire_offer(third)
    assert transfers == [(_addr_hex(direct_alice).lower(), BOND)] * 2


def test_stats_disclose_sampling_and_evidence_risk(direct_vm, direct_deploy):
    stats = direct_deploy("contracts/uptime_bond.py").get_stats()
    assert stats["version"] == "0.2.0-studionet"
    assert stats["sampling_policy"] == "AUTONOMOUS_FINALIZED_SELF_CALLS"
    assert stats["missing_evidence_payout"] == "BENEFICIARY"
    assert stats["evidence_risk_bearer"] == "PROVIDER"
    assert stats["check_timeout_secs"] == "300"
    assert stats["fee_bps"] == "0" and stats["admin_controls"] is False
