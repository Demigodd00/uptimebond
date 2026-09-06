# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
import hashlib
import re
from datetime import datetime, timezone

ERROR_EXPECTED = "[EXPECTED]"

VERSION = "0.1.0-studionet"
MIN_BOND_ATTO = 10 ** 15
MAX_BOND_ATTO = 10 * 10 ** 18
MIN_SETUP_LEAD_SECS = 120
MIN_ACCEPTANCE_BUFFER_SECS = 60
MIN_INTERVAL_SECS = 60
MAX_INTERVAL_SECS = 24 * 60 * 60
MIN_SLOT_COUNT = 2
MAX_SLOT_COUNT = 12
MAX_MONITORING_SECS = 7 * 24 * 60 * 60
MAX_SERVICE_NAME_CHARS = 80
MAX_ENDPOINT_URL_CHARS = 360
MIN_PROOF_TOKEN_CHARS = 8
MAX_PROOF_TOKEN_CHARS = 96
MAX_RESPONSE_BYTES = 16_000
MAX_PAGE_SIZE = 25


def _now_unix() -> int:
    return int(datetime.fromisoformat(gl.message_raw["datetime"]).timestamp())


def _to_iso(unix: int) -> str:
    return datetime.fromtimestamp(unix, tz=timezone.utc).isoformat()


def _clean_endpoint_url(value: str) -> str:
    url = value.strip()
    if (
        len(url) < 12
        or len(url) > MAX_ENDPOINT_URL_CHARS
        or "\x00" in url
        or re.search(r"\s", url)
    ):
        raise gl.vm.UserError(f"{ERROR_EXPECTED} health endpoint URL is invalid")
    if re.fullmatch(r"https://[^/]+(?:/.*)?", url) is None:
        raise gl.vm.UserError(f"{ERROR_EXPECTED} health endpoint must use public HTTPS")
    authority = url[8:].split("/", 1)[0]
    if not authority or "@" in authority or "[" in authority or "]" in authority:
        raise gl.vm.UserError(f"{ERROR_EXPECTED} health endpoint authority is invalid")
    authority_parts = authority.split(":", 1)
    if len(authority_parts) == 2 and (
        re.fullmatch(r"[0-9]{1,5}", authority_parts[1]) is None
        or int(authority_parts[1]) > 65535
    ):
        raise gl.vm.UserError(f"{ERROR_EXPECTED} health endpoint port is invalid")
    host = authority_parts[0].lower().rstrip(".")
    if "." not in host or host == "localhost" or host.endswith(".local"):
        raise gl.vm.UserError(f"{ERROR_EXPECTED} health endpoint must use a public host")
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host) is not None:
        raise gl.vm.UserError(f"{ERROR_EXPECTED} IP-literal health endpoints are not supported")
    if re.fullmatch(r"[a-z0-9.-]+", host) is None or ".." in host:
        raise gl.vm.UserError(f"{ERROR_EXPECTED} health endpoint host is invalid")
    return url


def _clean_service_name(value: str) -> str:
    name = value.strip()
    if len(name) == 0 or len(name) > MAX_SERVICE_NAME_CHARS or "\x00" in name:
        raise gl.vm.UserError(
            f"{ERROR_EXPECTED} service name must be 1..{MAX_SERVICE_NAME_CHARS} characters"
        )
    return name


def _clean_proof_token(value: str) -> str:
    token = value.strip()
    if (
        len(token) < MIN_PROOF_TOKEN_CHARS
        or len(token) > MAX_PROOF_TOKEN_CHARS
        or re.fullmatch(r"[A-Za-z0-9._:/-]+", token) is None
    ):
        raise gl.vm.UserError(
            f"{ERROR_EXPECTED} proof token must be {MIN_PROOF_TOKEN_CHARS}..{MAX_PROOF_TOKEN_CHARS} URL-safe characters"
        )
    return token


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


@allow_storage
@dataclass
class Bond:
    id: str
    service_name: str
    endpoint_url: str
    expected_status: u256
    proof_token: str
    provider: Address
    beneficiary: Address
    bond_atto: u256
    accept_by_unix: u256
    starts_at_unix: u256
    interval_secs: u256
    slot_count: u256
    min_observations: u256
    max_failures: u256
    created_at_unix: u256
    created_at_iso: str
    accepted_at_unix: u256
    accepted_at_iso: str
    status: str
    readiness_exists: bool
    readiness_http_status: u256
    readiness_body_digest: str
    readiness_body_bytes: u256
    readiness_checked_at_unix: u256
    readiness_checked_at_iso: str
    observed_count: u256
    passed_count: u256
    failed_count: u256
    cancellation_requested: bool
    cancellation_requested_by: Address
    result: str
    settled_at_unix: u256
    settled_at_iso: str
    payout_recipient: Address
    payout_atto: u256


@allow_storage
@dataclass
class Observation:
    bond_id: str
    slot_index: u256
    result: str
    http_status: u256
    status_matched: bool
    token_present: bool
    body_within_limit: bool
    body_digest: str
    body_bytes: u256
    observed_at_unix: u256
    observed_at_iso: str


class UptimeBond(gl.Contract):
    next_id: u256
    total_created: u256
    total_finalized: u256
    total_met: u256
    total_breached: u256
    total_inconclusive: u256
    total_locked_atto: u256
    total_returned_to_providers_atto: u256
    total_paid_to_beneficiaries_atto: u256
    bonds: TreeMap[str, Bond]
    bond_ids: DynArray[str]
    observations: TreeMap[str, Observation]

    def __init__(self):
        self.next_id = u256(1)
        self.total_created = u256(0)
        self.total_finalized = u256(0)
        self.total_met = u256(0)
        self.total_breached = u256(0)
        self.total_inconclusive = u256(0)
        self.total_locked_atto = u256(0)
        self.total_returned_to_providers_atto = u256(0)
        self.total_paid_to_beneficiaries_atto = u256(0)

    @gl.public.write.payable
    def create_bond(
        self,
        service_name: str,
        endpoint_url: str,
        beneficiary: str,
        expected_status: u256,
        proof_token: str,
        accept_by_unix: u256,
        starts_at_unix: u256,
        interval_secs: u256,
        slot_count: u256,
        min_observations: u256,
        max_failures: u256,
    ) -> str:
        amount = gl.message.value
        now = _now_unix()
        service_name = _clean_service_name(service_name)
        endpoint_url = _clean_endpoint_url(endpoint_url)
        proof_token = _clean_proof_token(proof_token)

        if int(amount) < MIN_BOND_ATTO or int(amount) > MAX_BOND_ATTO:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} bond must be between {MIN_BOND_ATTO} and {MAX_BOND_ATTO} atto"
            )
        if re.fullmatch(r"0x[0-9a-fA-F]{40}", beneficiary) is None:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} beneficiary address is invalid")
        beneficiary_address = Address(beneficiary)
        if beneficiary_address == gl.message.sender_address:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} provider and beneficiary must be different wallets")
        if str(beneficiary_address).lower() == "0x0000000000000000000000000000000000000000":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} beneficiary cannot be the zero address")
        if int(expected_status) < 100 or int(expected_status) > 599:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} expected HTTP status must be 100..599")
        if int(accept_by_unix) < now + MIN_SETUP_LEAD_SECS:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} acceptance deadline must be at least {MIN_SETUP_LEAD_SECS}s in the future"
            )
        if int(starts_at_unix) < int(accept_by_unix) + MIN_ACCEPTANCE_BUFFER_SECS:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} monitoring must start at least {MIN_ACCEPTANCE_BUFFER_SECS}s after the acceptance deadline"
            )
        if int(interval_secs) < MIN_INTERVAL_SECS or int(interval_secs) > MAX_INTERVAL_SECS:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} interval must be {MIN_INTERVAL_SECS}..{MAX_INTERVAL_SECS} seconds"
            )
        if int(slot_count) < MIN_SLOT_COUNT or int(slot_count) > MAX_SLOT_COUNT:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} slot count must be {MIN_SLOT_COUNT}..{MAX_SLOT_COUNT}"
            )
        duration = int(interval_secs) * int(slot_count)
        if duration > MAX_MONITORING_SECS:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} monitoring duration cannot exceed {MAX_MONITORING_SECS} seconds"
            )
        if int(min_observations) < 1 or int(min_observations) > int(slot_count):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} minimum observations must be 1..slot count"
            )
        if int(max_failures) >= int(min_observations):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} allowed failures must be lower than minimum observations"
            )

        bond_id = "ub-" + str(int(self.next_id))
        self.next_id = u256(int(self.next_id) + 1)
        self.bonds[bond_id] = Bond(
            id=bond_id,
            service_name=service_name,
            endpoint_url=endpoint_url,
            expected_status=expected_status,
            proof_token=proof_token,
            provider=gl.message.sender_address,
            beneficiary=beneficiary_address,
            bond_atto=amount,
            accept_by_unix=accept_by_unix,
            starts_at_unix=starts_at_unix,
            interval_secs=interval_secs,
            slot_count=slot_count,
            min_observations=min_observations,
            max_failures=max_failures,
            created_at_unix=u256(now),
            created_at_iso=_to_iso(now),
            accepted_at_unix=u256(0),
            accepted_at_iso="",
            status="OFFERED",
            readiness_exists=False,
            readiness_http_status=u256(0),
            readiness_body_digest="",
            readiness_body_bytes=u256(0),
            readiness_checked_at_unix=u256(0),
            readiness_checked_at_iso="",
            observed_count=u256(0),
            passed_count=u256(0),
            failed_count=u256(0),
            cancellation_requested=False,
            cancellation_requested_by=gl.message.sender_address,
            result="",
            settled_at_unix=u256(0),
            settled_at_iso="",
            payout_recipient=gl.message.sender_address,
            payout_atto=u256(0),
        )
        self.bond_ids.append(bond_id)
        self.total_created = u256(int(self.total_created) + 1)
        self.total_locked_atto = u256(int(self.total_locked_atto) + int(amount))
        return bond_id

    def _probe(self, endpoint_url: str, expected_status: u256, proof_token: str) -> dict:
        def fetch_and_normalize() -> dict:
            response = gl.nondet.web.get(endpoint_url)
            body = response.body
            body_bytes = len(body)
            body_within_limit = body_bytes <= MAX_RESPONSE_BYTES
            token_present = False
            if body_within_limit:
                try:
                    text = body.decode("utf-8")
                    token_present = proof_token in text
                except UnicodeDecodeError:
                    token_present = False

            status = int(response.status)
            status_matched = status == int(expected_status)
            if not body_within_limit:
                result = "FAIL_BODY_LIMIT"
            elif not status_matched and not token_present:
                result = "FAIL_STATUS_AND_TOKEN"
            elif not status_matched:
                result = "FAIL_STATUS"
            elif not token_present:
                result = "FAIL_TOKEN"
            else:
                result = "PASS"

            return {
                "result": result,
                "http_status": status,
                "status_matched": status_matched,
                "token_present": token_present,
                "body_within_limit": body_within_limit,
                "body_digest": hashlib.sha256(body).hexdigest(),
                "body_bytes": body_bytes,
            }

        def validator_fn(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            validator_result = fetch_and_normalize()
            leader_result = leaders_res.calldata
            return (
                leader_result["result"] == validator_result["result"]
                and int(leader_result["http_status"])
                == int(validator_result["http_status"])
                and leader_result["status_matched"]
                == validator_result["status_matched"]
                and leader_result["token_present"]
                == validator_result["token_present"]
                and leader_result["body_within_limit"]
                == validator_result["body_within_limit"]
                and leader_result["body_digest"]
                == validator_result["body_digest"]
                and int(leader_result["body_bytes"])
                == int(validator_result["body_bytes"])
            )

        return gl.vm.run_nondet_unsafe(fetch_and_normalize, validator_fn)

    @gl.public.write
    def verify_readiness(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if gl.message.sender_address != bond.provider:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only the provider can verify readiness")
        if bond.status != "OFFERED":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only offered bonds can verify readiness")
        if _now_unix() >= int(bond.accept_by_unix):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} acceptance deadline has passed")

        probe = self._probe(bond.endpoint_url, bond.expected_status, bond.proof_token)
        if probe["result"] != "PASS":
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} endpoint readiness failed: {probe['result']}"
            )

        checked_at = _now_unix()
        bond.status = "READY"
        bond.readiness_exists = True
        bond.readiness_http_status = u256(probe["http_status"])
        bond.readiness_body_digest = probe["body_digest"]
        bond.readiness_body_bytes = u256(probe["body_bytes"])
        bond.readiness_checked_at_unix = u256(checked_at)
        bond.readiness_checked_at_iso = _to_iso(checked_at)
        self.bonds[bond_id] = bond

    @gl.public.write
    def accept_bond(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if gl.message.sender_address != bond.beneficiary:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only the beneficiary can accept")
        if bond.status != "READY":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} bond is not ready for acceptance")
        now = _now_unix()
        if now >= int(bond.accept_by_unix):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} acceptance deadline has passed")
        if now >= int(bond.starts_at_unix):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} monitoring has already started")

        bond.status = "ACTIVE"
        bond.accepted_at_unix = u256(now)
        bond.accepted_at_iso = _to_iso(now)
        self.bonds[bond_id] = bond

    @gl.public.write
    def decline_bond(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if gl.message.sender_address != bond.beneficiary:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only the beneficiary can decline")
        if bond.status not in ("OFFERED", "READY"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} bond can no longer be declined")
        self._return_to_provider(bond, bond_id, "DECLINED", "BENEFICIARY_DECLINED")

    @gl.public.write
    def cancel_offer(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if gl.message.sender_address != bond.provider:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only the provider can cancel the offer")
        if bond.status not in ("OFFERED", "READY"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} accepted bonds require mutual cancellation")
        self._return_to_provider(bond, bond_id, "CANCELLED", "PROVIDER_CANCELLED")

    @gl.public.write
    def expire_offer(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if bond.status not in ("OFFERED", "READY"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only unaccepted offers can expire")
        if _now_unix() <= int(bond.accept_by_unix):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} acceptance window is still open")
        self._return_to_provider(bond, bond_id, "EXPIRED", "ACCEPTANCE_EXPIRED")

    @gl.public.write
    def request_cancellation(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        sender = gl.message.sender_address
        if bond.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only active bonds use mutual cancellation")
        if sender != bond.provider and sender != bond.beneficiary:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only a participant can request cancellation")
        if _now_unix() >= self._ends_at(bond):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} monitoring has ended; finalize the bond")

        if not bond.cancellation_requested:
            bond.cancellation_requested = True
            bond.cancellation_requested_by = sender
            self.bonds[bond_id] = bond
            return
        if bond.cancellation_requested_by == sender:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} cancellation is already awaiting the other participant")
        self._return_to_provider(bond, bond_id, "CANCELLED", "MUTUAL_CANCELLATION")

    @gl.public.write
    def withdraw_cancellation_request(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if bond.status != "ACTIVE" or not bond.cancellation_requested:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} no active cancellation request")
        if gl.message.sender_address != bond.cancellation_requested_by:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only the requester can withdraw cancellation")
        bond.cancellation_requested = False
        self.bonds[bond_id] = bond

    @gl.public.write
    def record_observation(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if bond.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only active bonds can be observed")
        now = _now_unix()
        ends_at = self._ends_at(bond)
        if now < int(bond.starts_at_unix):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} monitoring has not started")
        if now >= ends_at:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} monitoring has ended")

        slot_index = (now - int(bond.starts_at_unix)) // int(bond.interval_secs)
        key = self._observation_key(bond_id, slot_index)
        if key in self.observations:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} current monitoring slot is already recorded")

        probe = self._probe(bond.endpoint_url, bond.expected_status, bond.proof_token)
        self.observations[key] = Observation(
            bond_id=bond_id,
            slot_index=u256(slot_index),
            result=probe["result"],
            http_status=u256(probe["http_status"]),
            status_matched=probe["status_matched"],
            token_present=probe["token_present"],
            body_within_limit=probe["body_within_limit"],
            body_digest=probe["body_digest"],
            body_bytes=u256(probe["body_bytes"]),
            observed_at_unix=u256(now),
            observed_at_iso=_to_iso(now),
        )
        bond.observed_count = u256(int(bond.observed_count) + 1)
        if probe["result"] == "PASS":
            bond.passed_count = u256(int(bond.passed_count) + 1)
        else:
            bond.failed_count = u256(int(bond.failed_count) + 1)
        self.bonds[bond_id] = bond

    @gl.public.write
    def finalize_bond(self, bond_id: str) -> None:
        bond = self._get_bond(bond_id)
        if bond.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only active bonds can be finalized")
        if _now_unix() < self._ends_at(bond):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} monitoring is still active")

        if int(bond.failed_count) > int(bond.max_failures):
            self._pay_beneficiary(bond, bond_id)
        elif int(bond.observed_count) < int(bond.min_observations):
            self.total_inconclusive = u256(int(self.total_inconclusive) + 1)
            self._return_to_provider(bond, bond_id, "INCONCLUSIVE", "INSUFFICIENT_OBSERVATIONS")
        else:
            self.total_met = u256(int(self.total_met) + 1)
            self._return_to_provider(bond, bond_id, "MET", "SLA_MET")

    def _pay_beneficiary(self, bond: Bond, bond_id: str) -> None:
        amount = bond.bond_atto
        settled_at = _now_unix()
        bond.status = "BREACHED"
        bond.result = "FAILURE_ALLOWANCE_EXCEEDED"
        bond.settled_at_unix = u256(settled_at)
        bond.settled_at_iso = _to_iso(settled_at)
        bond.payout_recipient = bond.beneficiary
        bond.payout_atto = amount
        bond.cancellation_requested = False
        self.bonds[bond_id] = bond
        self.total_finalized = u256(int(self.total_finalized) + 1)
        self.total_breached = u256(int(self.total_breached) + 1)
        self.total_locked_atto = u256(int(self.total_locked_atto) - int(amount))
        self.total_paid_to_beneficiaries_atto = u256(
            int(self.total_paid_to_beneficiaries_atto) + int(amount)
        )
        _Recipient(bond.beneficiary).emit_transfer(value=amount)

    def _return_to_provider(self, bond: Bond, bond_id: str, status: str, result: str) -> None:
        amount = bond.bond_atto
        settled_at = _now_unix()
        bond.status = status
        bond.result = result
        bond.settled_at_unix = u256(settled_at)
        bond.settled_at_iso = _to_iso(settled_at)
        bond.payout_recipient = bond.provider
        bond.payout_atto = amount
        bond.cancellation_requested = False
        self.bonds[bond_id] = bond
        self.total_finalized = u256(int(self.total_finalized) + 1)
        self.total_locked_atto = u256(int(self.total_locked_atto) - int(amount))
        self.total_returned_to_providers_atto = u256(
            int(self.total_returned_to_providers_atto) + int(amount)
        )
        _Recipient(bond.provider).emit_transfer(value=amount)

    def _get_bond(self, bond_id: str) -> Bond:
        if bond_id not in self.bonds:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} bond not found: {bond_id}")
        return self.bonds[bond_id]

    def _ends_at(self, bond: Bond) -> int:
        return int(bond.starts_at_unix) + int(bond.interval_secs) * int(bond.slot_count)

    def _observation_key(self, bond_id: str, slot_index: int) -> str:
        return bond_id + ":" + str(slot_index)

    def _observation_dict(self, observation: Observation) -> dict:
        return {
            "slot_index": str(int(observation.slot_index)),
            "result": observation.result,
            "http_status": str(int(observation.http_status)),
            "status_matched": observation.status_matched,
            "token_present": observation.token_present,
            "body_within_limit": observation.body_within_limit,
            "body_digest": observation.body_digest,
            "body_bytes": str(int(observation.body_bytes)),
            "observed_at_unix": str(int(observation.observed_at_unix)),
            "observed_at_iso": observation.observed_at_iso,
            "provenance": "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH",
        }

    @gl.public.view
    def get_bond(self, bond_id: str) -> dict:
        bond = self._get_bond(bond_id)
        now = _now_unix()
        ends_at = self._ends_at(bond)
        current_slot = -1
        current_slot_recorded = False
        if now >= int(bond.starts_at_unix) and now < ends_at:
            current_slot = (now - int(bond.starts_at_unix)) // int(bond.interval_secs)
            current_slot_recorded = (
                self._observation_key(bond_id, current_slot) in self.observations
            )
        uptime_bps = (
            (int(bond.passed_count) * 10000) // int(bond.observed_count)
            if int(bond.observed_count) > 0
            else 0
        )
        return {
            "id": bond.id,
            "service_name": bond.service_name,
            "endpoint_url": bond.endpoint_url,
            "expected_status": str(int(bond.expected_status)),
            "proof_token": bond.proof_token,
            "provider": str(bond.provider),
            "beneficiary": str(bond.beneficiary),
            "bond_atto": str(int(bond.bond_atto)),
            "accept_by_unix": str(int(bond.accept_by_unix)),
            "starts_at_unix": str(int(bond.starts_at_unix)),
            "ends_at_unix": str(ends_at),
            "interval_secs": str(int(bond.interval_secs)),
            "slot_count": str(int(bond.slot_count)),
            "min_observations": str(int(bond.min_observations)),
            "max_failures": str(int(bond.max_failures)),
            "created_at_unix": str(int(bond.created_at_unix)),
            "created_at_iso": bond.created_at_iso,
            "accepted_at_unix": str(int(bond.accepted_at_unix)),
            "accepted_at_iso": bond.accepted_at_iso,
            "status": bond.status,
            "readiness": {
                "exists": bond.readiness_exists,
                "http_status": str(int(bond.readiness_http_status)),
                "body_digest": bond.readiness_body_digest,
                "body_bytes": str(int(bond.readiness_body_bytes)),
                "checked_at_unix": str(int(bond.readiness_checked_at_unix)),
                "checked_at_iso": bond.readiness_checked_at_iso,
                "provenance": "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH",
            },
            "observed_count": str(int(bond.observed_count)),
            "passed_count": str(int(bond.passed_count)),
            "failed_count": str(int(bond.failed_count)),
            "uptime_bps": str(uptime_bps),
            "current_slot": str(current_slot),
            "current_slot_recorded": current_slot_recorded,
            "can_observe": (
                bond.status == "ACTIVE"
                and current_slot >= 0
                and not current_slot_recorded
            ),
            "can_finalize": bond.status == "ACTIVE" and now >= ends_at,
            "can_expire": (
                bond.status in ("OFFERED", "READY")
                and now > int(bond.accept_by_unix)
            ),
            "cancellation_requested": bond.cancellation_requested,
            "cancellation_requested_by": (
                str(bond.cancellation_requested_by)
                if bond.cancellation_requested
                else ""
            ),
            "result": bond.result,
            "settled_at_unix": str(int(bond.settled_at_unix)),
            "settled_at_iso": bond.settled_at_iso,
            "payout_recipient": (
                str(bond.payout_recipient) if int(bond.payout_atto) > 0 else ""
            ),
            "payout_atto": str(int(bond.payout_atto)),
        }

    @gl.public.view
    def get_observations(self, bond_id: str) -> dict:
        bond = self._get_bond(bond_id)
        items = []
        slot_index = 0
        while slot_index < int(bond.slot_count):
            key = self._observation_key(bond_id, slot_index)
            if key in self.observations:
                items.append(self._observation_dict(self.observations[key]))
            slot_index += 1
        return {
            "bond_id": bond_id,
            "total": str(len(items)),
            "items": items,
        }

    @gl.public.view
    def list_bonds(self, offset: u256, count: u256) -> dict:
        total = len(self.bond_ids)
        start = int(offset)
        end = min(start + min(int(count), MAX_PAGE_SIZE), total)
        items = []
        index = start
        while index < end:
            bond_id = self.bond_ids[index]
            bond = self.bonds[bond_id]
            items.append(
                {
                    "id": bond.id,
                    "service_name": bond.service_name,
                    "status": bond.status,
                    "provider": str(bond.provider),
                    "beneficiary": str(bond.beneficiary),
                    "bond_atto": str(int(bond.bond_atto)),
                    "observed_count": str(int(bond.observed_count)),
                    "passed_count": str(int(bond.passed_count)),
                    "failed_count": str(int(bond.failed_count)),
                }
            )
            index += 1
        return {"total": str(total), "items": items}

    @gl.public.view
    def get_stats(self) -> dict:
        return {
            "total_created": str(int(self.total_created)),
            "total_finalized": str(int(self.total_finalized)),
            "total_met": str(int(self.total_met)),
            "total_breached": str(int(self.total_breached)),
            "total_inconclusive": str(int(self.total_inconclusive)),
            "total_locked_atto": str(int(self.total_locked_atto)),
            "total_returned_to_providers_atto": str(
                int(self.total_returned_to_providers_atto)
            ),
            "total_paid_to_beneficiaries_atto": str(
                int(self.total_paid_to_beneficiaries_atto)
            ),
            "fee_bps": "0",
            "admin_controls": False,
            "experimental": True,
            "max_page_size": str(MAX_PAGE_SIZE),
            "max_response_bytes": str(MAX_RESPONSE_BYTES),
            "probe_policy": "STRICT_INDEPENDENT_STATUS_TOKEN_SIZE_AND_SHA256",
            "version": VERSION,
        }
