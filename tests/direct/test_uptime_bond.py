import hashlib
from datetime import datetime, timezone

import pytest


TEST_NOW_UNIX = 2_000_000_000
BOND = 10**18
ENDPOINT = "https://status.example.com/health"
TOKEN = "uptimebond-demo-v1"
UP_BODY = '{"service":"demo","proof":"uptimebond-demo-v1","status":"up"}'


def _addr_hex(address) -> str:
    if hasattr(address, "as_bytes"):
        raw = address.as_bytes
    elif isinstance(address, bytes):
        raw = address
    else:
        raw = bytes.fromhex(str(address).replace("0x", ""))
    return "0x" + raw.hex()


def _time(unix: int) -> str:
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _warp(direct_vm, unix: int) -> None:
    direct_vm.warp(_time(unix))


def _schedule() -> tuple[int, int]:
    return TEST_NOW_UNIX + 300, TEST_NOW_UNIX + 400


def _mock_endpoint(direct_vm, body=UP_BODY, status: int = 200) -> None:
    direct_vm.mock_web(
        r".*status\.example\.com/health.*",
        {"status": status, "body": body},
    )


def _create(
    direct_vm,
    contract,
    provider,
    beneficiary,
    *,
    amount: int = BOND,
    endpoint: str = ENDPOINT,
    expected_status: int = 200,
    token: str = TOKEN,
    accept_by: int | None = None,
    starts_at: int | None = None,
    interval: int = 60,
    slots: int = 3,
    minimum: int = 2,
    allowed_failures: int = 0,
) -> str:
    default_accept_by, default_starts_at = _schedule()
    direct_vm.sender = provider
    direct_vm.value = amount
    bond_id = contract.create_bond(
        "Demo API",
        endpoint,
        _addr_hex(beneficiary),
        expected_status,
        token,
        accept_by if accept_by is not None else default_accept_by,
        starts_at if starts_at is not None else default_starts_at,
        interval,
        slots,
        minimum,
        allowed_failures,
    )
    direct_vm.value = 0
    return bond_id


def _ready(direct_vm, contract, bond_id: str, provider) -> None:
    direct_vm.sender = provider
    _mock_endpoint(direct_vm)
    contract.verify_readiness(bond_id)


def _activate(direct_vm, contract, bond_id: str, provider, beneficiary) -> None:
    _ready(direct_vm, contract, bond_id, provider)
    direct_vm.sender = beneficiary
    contract.accept_bond(bond_id)


def _capture_transfers(direct_vm) -> list[tuple[str, int]]:
    transfers: list[tuple[str, int]] = []

    def capture(_vm, request):
        if "EthSend" in request:
            transfer = request["EthSend"]
            transfers.append((str(transfer["address"]).lower(), int(transfer["value"])))
            return {"ok": None}
        return None

    direct_vm._gl_call_hook = capture
    return transfers


def test_create_bond_stores_immutable_terms_and_liability(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)

    bond = contract.get_bond(bond_id)
    assert bond["id"] == "ub-1"
    assert bond["status"] == "OFFERED"
    assert bond["service_name"] == "Demo API"
    assert bond["endpoint_url"] == ENDPOINT
    assert bond["expected_status"] == "200"
    assert bond["proof_token"] == TOKEN
    assert bond["provider"].lower() == _addr_hex(direct_alice).lower()
    assert bond["beneficiary"].lower() == _addr_hex(direct_bob).lower()
    assert bond["bond_atto"] == str(BOND)
    assert bond["ends_at_unix"] == str(TEST_NOW_UNIX + 580)
    assert bond["payout_recipient"] == ""
    assert contract.get_stats()["total_locked_atto"] == str(BOND)
    assert contract.get_stats()["admin_controls"] is False
    assert contract.get_stats()["fee_bps"] == "0"


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com/health",
        "https://localhost/health",
        "https://127.0.0.1/health",
        "https://user@example.com/health",
        "https://example..com/health",
        "https://example.com:bad/health",
        "https://example.com/bad path",
    ],
)
def test_rejects_non_public_or_malformed_endpoints(
    endpoint, direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    with pytest.raises(Exception, match="health endpoint"):
        _create(direct_vm, contract, direct_alice, direct_bob, endpoint=endpoint)
    direct_vm.value = 0


def test_rejects_invalid_value_roles_and_probe_terms(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")

    with pytest.raises(Exception, match="bond must be between"):
        _create(direct_vm, contract, direct_alice, direct_bob, amount=0)
    direct_vm.value = 0
    with pytest.raises(Exception, match="different wallets"):
        _create(direct_vm, contract, direct_alice, direct_alice)
    direct_vm.value = 0
    with pytest.raises(Exception, match="HTTP status"):
        _create(direct_vm, contract, direct_alice, direct_bob, expected_status=99)
    direct_vm.value = 0
    with pytest.raises(Exception, match="proof token"):
        _create(direct_vm, contract, direct_alice, direct_bob, token="short")
    direct_vm.value = 0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"accept_by": TEST_NOW_UNIX + 60}, "acceptance deadline"),
        (
            {"accept_by": TEST_NOW_UNIX + 300, "starts_at": TEST_NOW_UNIX + 320},
            "monitoring must start",
        ),
        ({"interval": 59}, "interval"),
        ({"slots": 1}, "slot count"),
        ({"minimum": 4}, "minimum observations"),
        ({"minimum": 2, "allowed_failures": 2}, "allowed failures"),
    ],
)
def test_rejects_unsafe_schedule_terms(
    changes, message, direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    with pytest.raises(Exception, match=message):
        _create(direct_vm, contract, direct_alice, direct_bob, **changes)
    direct_vm.value = 0


def test_readiness_requires_provider_and_exact_passing_response(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="only the provider"):
        contract.verify_readiness(bond_id)

    direct_vm.sender = direct_alice
    _mock_endpoint(direct_vm, body='{"status":"up"}')
    with pytest.raises(Exception, match="FAIL_TOKEN"):
        contract.verify_readiness(bond_id)
    assert contract.get_bond(bond_id)["status"] == "OFFERED"

    direct_vm.clear_mocks()
    _mock_endpoint(direct_vm)
    contract.verify_readiness(bond_id)
    readiness = contract.get_bond(bond_id)["readiness"]
    assert contract.get_bond(bond_id)["status"] == "READY"
    assert readiness["exists"] is True
    assert readiness["http_status"] == "200"
    assert readiness["body_digest"] == hashlib.sha256(UP_BODY.encode()).hexdigest()
    assert readiness["provenance"] == "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH"


def test_strict_consensus_rejects_different_response_bytes(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _ready(direct_vm, contract, bond_id, direct_alice)

    direct_vm.clear_mocks()
    _mock_endpoint(
        direct_vm,
        body='{"service":"changed","proof":"uptimebond-demo-v1","status":"up"}',
    )
    assert direct_vm.run_validator() is False


def test_only_beneficiary_accepts_a_ready_unexpired_bond(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="not ready"):
        contract.accept_bond(bond_id)

    _ready(direct_vm, contract, bond_id, direct_alice)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="only the beneficiary"):
        contract.accept_bond(bond_id)

    direct_vm.sender = direct_bob
    contract.accept_bond(bond_id)
    assert contract.get_bond(bond_id)["status"] == "ACTIVE"
    assert contract.get_bond(bond_id)["accepted_at_unix"] == str(TEST_NOW_UNIX)


def test_cancel_decline_and_expire_return_exact_bonds(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    transfers = _capture_transfers(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")

    cancel_id = _create(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    contract.cancel_offer(cancel_id)

    decline_id = _create(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    contract.decline_bond(decline_id)

    expire_id = _create(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="window is still open"):
        contract.expire_offer(expire_id)
    _warp(direct_vm, TEST_NOW_UNIX + 301)
    contract.expire_offer(expire_id)

    assert contract.get_bond(cancel_id)["status"] == "CANCELLED"
    assert contract.get_bond(decline_id)["status"] == "DECLINED"
    assert contract.get_bond(expire_id)["status"] == "EXPIRED"
    assert contract.get_stats()["total_locked_atto"] == "0"
    assert transfers == [(_addr_hex(direct_alice).lower(), BOND)] * 3


def test_observation_is_permissionless_fixed_to_current_slot_and_append_only(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="has not started"):
        contract.record_observation(bond_id)

    _warp(direct_vm, TEST_NOW_UNIX + 401)
    direct_vm.clear_mocks()
    _mock_endpoint(direct_vm)
    contract.record_observation(bond_id)
    with pytest.raises(Exception, match="already recorded"):
        contract.record_observation(bond_id)

    observation = contract.get_observations(bond_id)["items"][0]
    assert observation["slot_index"] == "0"
    assert observation["result"] == "PASS"
    assert observation["http_status"] == "200"
    assert observation["status_matched"] is True
    assert observation["token_present"] is True
    assert observation["body_digest"] == hashlib.sha256(UP_BODY.encode()).hexdigest()
    assert contract.get_bond(bond_id)["passed_count"] == "1"


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (503, UP_BODY, "FAIL_STATUS"),
        (200, '{"status":"up"}', "FAIL_TOKEN"),
        (503, '{"status":"down"}', "FAIL_STATUS_AND_TOKEN"),
        (200, "x" * 16_001, "FAIL_BODY_LIMIT"),
    ],
)
def test_probe_records_each_objective_failure_code(
    status, body, expected, direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)
    _warp(direct_vm, TEST_NOW_UNIX + 401)
    direct_vm.clear_mocks()
    _mock_endpoint(direct_vm, body=body, status=status)
    contract.record_observation(bond_id)

    item = contract.get_observations(bond_id)["items"][0]
    assert item["result"] == expected
    assert contract.get_bond(bond_id)["failed_count"] == "1"


def test_met_bond_returns_value_to_provider_after_enough_checks(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    transfers = _capture_transfers(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)

    for timestamp in (TEST_NOW_UNIX + 401, TEST_NOW_UNIX + 461):
        _warp(direct_vm, timestamp)
        direct_vm.clear_mocks()
        _mock_endpoint(direct_vm)
        direct_vm.sender = direct_charlie
        contract.record_observation(bond_id)

    with pytest.raises(Exception, match="still active"):
        contract.finalize_bond(bond_id)
    _warp(direct_vm, TEST_NOW_UNIX + 580)
    contract.finalize_bond(bond_id)

    bond = contract.get_bond(bond_id)
    assert bond["status"] == "MET"
    assert bond["result"] == "SLA_MET"
    assert bond["payout_recipient"].lower() == _addr_hex(direct_alice).lower()
    assert bond["uptime_bps"] == "10000"
    assert transfers == [(_addr_hex(direct_alice).lower(), BOND)]
    stats = contract.get_stats()
    assert stats["total_met"] == "1"
    assert stats["total_locked_atto"] == "0"


def test_breached_bond_pays_beneficiary_and_cannot_pay_twice(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    transfers = _capture_transfers(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)

    _warp(direct_vm, TEST_NOW_UNIX + 401)
    direct_vm.clear_mocks()
    _mock_endpoint(direct_vm, status=503)
    contract.record_observation(bond_id)
    _warp(direct_vm, TEST_NOW_UNIX + 580)
    contract.finalize_bond(bond_id)

    bond = contract.get_bond(bond_id)
    assert bond["status"] == "BREACHED"
    assert bond["payout_recipient"].lower() == _addr_hex(direct_bob).lower()
    assert transfers == [(_addr_hex(direct_bob).lower(), BOND)]
    assert contract.get_stats()["total_breached"] == "1"
    assert contract.get_stats()["total_paid_to_beneficiaries_atto"] == str(BOND)
    with pytest.raises(Exception, match="only active bonds"):
        contract.finalize_bond(bond_id)
    assert len(transfers) == 1


def test_insufficient_evidence_is_explicit_and_returns_provider_bond(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    transfers = _capture_transfers(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)

    _warp(direct_vm, TEST_NOW_UNIX + 580)
    contract.finalize_bond(bond_id)
    bond = contract.get_bond(bond_id)
    assert bond["status"] == "INCONCLUSIVE"
    assert bond["result"] == "INSUFFICIENT_OBSERVATIONS"
    assert bond["observed_count"] == "0"
    assert transfers == [(_addr_hex(direct_alice).lower(), BOND)]
    assert contract.get_stats()["total_inconclusive"] == "1"


def test_active_cancellation_requires_both_participants(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    transfers = _capture_transfers(direct_vm)
    contract = direct_deploy("contracts/uptime_bond.py")
    bond_id = _create(direct_vm, contract, direct_alice, direct_bob)
    _activate(direct_vm, contract, bond_id, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="only a participant"):
        contract.request_cancellation(bond_id)

    direct_vm.sender = direct_alice
    contract.request_cancellation(bond_id)
    assert contract.get_bond(bond_id)["cancellation_requested"] is True
    with pytest.raises(Exception, match="awaiting the other"):
        contract.request_cancellation(bond_id)

    contract.withdraw_cancellation_request(bond_id)
    assert contract.get_bond(bond_id)["cancellation_requested"] is False
    contract.request_cancellation(bond_id)

    direct_vm.sender = direct_bob
    contract.request_cancellation(bond_id)
    assert contract.get_bond(bond_id)["status"] == "CANCELLED"
    assert contract.get_bond(bond_id)["result"] == "MUTUAL_CANCELLATION"
    assert transfers == [(_addr_hex(direct_alice).lower(), BOND)]


def test_list_observations_and_stats_are_reviewable(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/uptime_bond.py")
    first = _create(direct_vm, contract, direct_alice, direct_bob)
    second = _create(direct_vm, contract, direct_alice, direct_bob)

    listing = contract.list_bonds(0, 25)
    assert listing["total"] == "2"
    assert [item["id"] for item in listing["items"]] == [first, second]
    assert listing["items"][0]["status"] == "OFFERED"
    assert contract.get_observations(first) == {
        "bond_id": first,
        "total": "0",
        "items": [],
    }

    stats = contract.get_stats()
    assert stats["version"] == "0.1.0-studionet"
    assert stats["probe_policy"] == "STRICT_INDEPENDENT_STATUS_TOKEN_SIZE_AND_SHA256"
    assert stats["max_response_bytes"] == "16000"
    assert stats["experimental"] is True
