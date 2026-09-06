"""Resume-safe exact-address acceptance for UptimeBond on StudioNet.

The script never deploys. It uses the recorded deployment signer plus two
domain-separated test accounts, journals every write before broadcast, and
resumes known hashes rather than blindly sending a duplicate transaction.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import requests
from eth_account import Account
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.client.genlayer_client import GenLayerClient
from web3 import Web3
from web3.logs import DISCARD

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_PATH = ROOT / "deployments" / "uptime_bond_studionet.json"
RECORD_PATH = ROOT / "deployments" / "uptime_bond_acceptance.json"
ENV_PATH = ROOT / ".env"
RPC_URL = "https://studio.genlayer.com/api"
STAKE = 10**15
ENDPOINT = os.environ.get(
    "UPTIMEBOND_TEST_ENDPOINT",
    "https://uptimebond-psi.vercel.app/api/demo-health",
).strip()
PROOF_TOKEN = os.environ.get("UPTIMEBOND_TEST_TOKEN", "uptimebond-demo-v1").strip()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def output(value) -> None:
    print(json.dumps(value, default=str), flush=True)


def load_saved_signer() -> str:
    configured = os.environ.get("UPTIMEBOND_PRIVATE_KEY", "").strip()
    if configured:
        return configured
    if not ENV_PATH.exists():
        raise RuntimeError("The saved StudioNet signer was not found")
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    if values.get("UPTIMEBOND_PRIVATE_KEY"):
        return values["UPTIMEBOND_PRIVATE_KEY"]
    raise RuntimeError("The saved StudioNet signer was not found")


def error_text(value) -> list[str]:
    texts: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            texts.extend(error_text(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            texts.extend(error_text(item))
    elif isinstance(value, str):
        texts.append(value)
        if 8 <= len(value) <= 100_000 and re.fullmatch(r"[A-Za-z0-9+/=]+", value):
            try:
                texts.append(base64.b64decode(value, validate=True).decode("utf-8", errors="ignore"))
            except (ValueError, TypeError):
                pass
    return texts


class Acceptance:
    def __init__(self) -> None:
        self.deployment = json.loads(DEPLOYMENT_PATH.read_text(encoding="utf-8"))
        if self.deployment.get("network") != "studionet":
            raise RuntimeError("Acceptance writes are restricted to StudioNet")
        provider = Account.from_key(load_saved_signer())
        if provider.address.lower() != str(self.deployment.get("deployer", "")).lower():
            raise RuntimeError("The saved signer does not match the recorded deployer")
        beneficiary = Account.from_key(
            hmac.new(provider.key, b"uptimebond/studionet/acceptance/beneficiary/v1", hashlib.sha256).digest()
        )
        observer = Account.from_key(
            hmac.new(provider.key, b"uptimebond/studionet/acceptance/observer/v1", hashlib.sha256).digest()
        )
        self.accounts = {
            "provider": provider,
            "beneficiary": beneficiary,
            "observer": observer,
        }
        self.address = self.deployment["address"]
        self.role = "provider"
        self.active_step: str | None = None
        self.last_request = 0.0
        self.http = requests.Session()
        self.client = GenLayerClient(deepcopy(studionet), provider)
        self.client.provider.make_request = self.rpc
        self.client.initialize_consensus_smart_contract()

        if RECORD_PATH.exists():
            self.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
            if self.record.get("contract", "").lower() != self.address.lower():
                raise RuntimeError("Existing acceptance record belongs to another deployment")
        else:
            self.record = {
                "network": "studionet",
                "contract": self.address,
                "source_sha256": self.deployment["source_sha256"],
                "started_at": timestamp(),
                "transactions": {},
                "assertions": {},
                "bonds": {},
            }
        self.record["wallets"] = {
            name: account.address for name, account in self.accounts.items()
        }
        self.record["fixture"] = {"endpoint": ENDPOINT, "proof_token": PROOF_TOKEN}
        self.save()

    def save(self) -> None:
        self.record["updated_at"] = timestamp()
        pending = RECORD_PATH.with_suffix(".json.tmp")
        pending.write_text(json.dumps(self.record, indent=2, default=str) + "\n", encoding="utf-8")
        for attempt in range(6):
            try:
                pending.replace(RECORD_PATH)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.25 * (attempt + 1))

    def rpc(self, method: str, params: list) -> dict:
        if method == "eth_sendRawTransaction" and self.active_step:
            entry = self.record["transactions"][self.active_step]
            entry["broadcast_attempted"] = True
            entry["evm_transaction_hash"] = Web3.to_hex(Web3.keccak(hexstr=params[0]))
            self.save()
        attempts = 1 if method == "eth_sendRawTransaction" else 5
        payload = None
        last_error = None
        for attempt in range(attempts):
            delay = 2.25 - (time.monotonic() - self.last_request)
            if delay > 0:
                time.sleep(delay)
            self.last_request = time.monotonic()
            try:
                response = self.http.post(
                    RPC_URL,
                    json={
                        "jsonrpc": "2.0",
                        "id": int(time.time() * 1000),
                        "method": method,
                        "params": params,
                    },
                    timeout=(10, 120),
                )
                response.raise_for_status()
                payload = response.json()
                break
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt + 1 == attempts:
                    raise
                time.sleep(min(10, 2**attempt))
        if payload is None:
            raise RuntimeError(f"{method}: RPC failed after retries: {last_error}")
        if payload.get("error"):
            error = payload["error"]
            raise RuntimeError(f"{method}: RPC {error.get('code')}: {error.get('message')}")
        if method == "eth_sendRawTransaction" and self.active_step:
            self.record["transactions"][self.active_step]["evm_transaction_hash"] = payload["result"]
            self.save()
        return payload

    def use_role(self, role: str) -> None:
        self.role = role
        self.client.local_account = self.accounts[role]

    def read(self, method: str, args: list):
        last_error: Exception | None = None
        for delay in (0, 2, 5):
            if delay:
                time.sleep(delay)
            try:
                return self.client.read_contract(
                    address=self.address,
                    function_name=method,
                    args=args,
                )
            except Exception as error:
                last_error = error
        raise RuntimeError(f"StudioNet read failed after retries: {last_error}")

    def preflight(self) -> None:
        source = base64.b64decode(self.rpc("gen_getContractCode", [self.address])["result"])
        digest = hashlib.sha256(source.replace(b"\r\n", b"\n")).hexdigest()
        if digest != self.deployment["source_sha256"]:
            raise RuntimeError("Deployed source differs from the recorded release")
        stats = self.read("get_stats", [])
        expected = {
            "fee_bps": "0",
            "admin_controls": False,
            "experimental": True,
            "max_page_size": "25",
            "max_response_bytes": "16000",
            "probe_policy": "STRICT_INDEPENDENT_STATUS_TOKEN_SIZE_AND_SHA256",
            "version": "0.1.0-studionet",
        }
        if any(stats.get(key) != value for key, value in expected.items()):
            raise RuntimeError("The exact-release configuration is not active")
        self.record["preflight"] = {
            "checked_at": timestamp(),
            "source_matches": True,
            "configuration_matches": True,
            "stats": stats,
        }
        self.save()
        output({"phase": "preflight", "passed": True, "contract": self.address})

    def write(
        self,
        step: str,
        method: str,
        args: list,
        *,
        value: int = 0,
        role: str = "provider",
        expected_error: str | None = None,
    ) -> dict:
        self.use_role(role)
        entries = self.record["transactions"]
        entry = entries.get(step)
        signature = (method, args, role, str(value), expected_error)
        if entry:
            recorded = (
                entry["method"],
                entry["args"],
                entry["role"],
                entry["value_atto"],
                entry["expected_error"],
            )
            if recorded != signature:
                raise RuntimeError(f"Recorded step {step} has different transaction arguments")
            if entry.get("checked"):
                return entry
        else:
            entry = {
                "method": method,
                "args": args,
                "role": role,
                "sender": self.accounts[role].address,
                "value_atto": str(value),
                "expected_error": expected_error,
                "started_at": timestamp(),
                "broadcast_attempted": False,
            }
            entries[step] = entry
            self.save()

        self.active_step = step
        if entry.get("broadcast_attempted") and not entry.get("transaction_hash"):
            receipt = self.client.w3.eth.get_transaction_receipt(entry["evm_transaction_hash"])
            consensus = self.client.w3.eth.contract(abi=self.client.chain.consensus_main_contract["abi"])
            events = consensus.get_event_by_name("NewTransaction").process_receipt(receipt, DISCARD)
            if not events:
                raise RuntimeError("Broadcast has no recoverable GenLayer transaction; do not resubmit")
            entry["transaction_hash"] = Web3.to_hex(events[0]["args"]["txId"])
            self.save()
        if not entry.get("transaction_hash"):
            output({"step": step, "state": "submitting", "method": method, "role": role})
            submitted = self.client.write_contract(
                address=self.address,
                function_name=method,
                args=args,
                value=value,
            )
            entry["transaction_hash"] = submitted if isinstance(submitted, str) else Web3.to_hex(submitted)
            self.save()

        output({"step": step, "transaction_hash": entry["transaction_hash"]})
        deadline = time.monotonic() + 900
        previous_status = None
        while time.monotonic() < deadline:
            receipt = self.rpc("eth_getTransactionByHash", [entry["transaction_hash"]])["result"]
            if not receipt:
                time.sleep(5)
                continue
            status = receipt.get("status")
            if status != previous_status:
                output({"step": step, "status": status})
                previous_status = status
            if status == "FINALIZED":
                success = tx_execution_succeeded(receipt)
                leaders = receipt.get("consensus_data", {}).get("leader_receipt", [])
                if isinstance(leaders, dict):
                    leaders = [leaders]
                entry.update(
                    {
                        "status": status,
                        "execution_succeeded": success,
                        "leader_execution_result": leaders[0].get("execution_result") if leaders else None,
                        "triggered_transactions": receipt.get("triggered_transactions", []),
                        "finished_at": timestamp(),
                    }
                )
                if expected_error:
                    matched = any(expected_error.lower() in text.lower() for text in error_text(receipt))
                    if success or not matched:
                        self.save()
                        raise RuntimeError(f"{step}: expected contract rejection was not verified")
                elif not success:
                    entry["failure_detail"] = leaders[0].get("genvm_result") if leaders else None
                    self.save()
                    raise RuntimeError(f"{step}: finalized with contract execution failure")
                entry["checked"] = True
                self.save()
                output({"step": step, "passed": True, "execution_succeeded": success})
                return entry
            time.sleep(5)
        raise RuntimeError(f"{step}: still pending; resume this same step instead of resubmitting")

    def assert_fields(self, key: str, actual: dict, expected: dict) -> dict:
        existing = self.record["assertions"].get(key)
        if existing:
            if existing["expected"] != expected:
                raise RuntimeError(f"Historical assertion {key} has different expectations")
            return existing["observed"]
        for field, value in expected.items():
            if actual.get(field) != value:
                raise AssertionError(f"{key}: {field} is {actual.get(field)!r}, expected {value!r}")
        self.record["assertions"][key] = {
            "checked_at": timestamp(),
            "expected": expected,
            "observed": actual,
        }
        self.save()
        output({"assertion": key, "passed": True})
        return actual

    def find_bond(self, service_name: str) -> str:
        matches = []
        offset = 0
        while True:
            page = self.read("list_bonds", [offset, 25])
            matches.extend(item for item in page["items"] if item["service_name"] == service_name)
            offset += len(page["items"])
            if offset >= int(page["total"]) or not page["items"]:
                break
        if len(matches) != 1:
            raise RuntimeError(f"Could not uniquely identify acceptance bond: {service_name}")
        return matches[0]["id"]

    def create(self, key: str, service_name: str, *, accept_lead: int, start_lead: int) -> str:
        step = f"create-{key}"
        existing = self.record["transactions"].get(step)
        args = existing["args"] if existing else [
            service_name,
            ENDPOINT,
            self.accounts["beneficiary"].address,
            200,
            PROOF_TOKEN,
            int(time.time()) + accept_lead,
            int(time.time()) + start_lead,
            120,
            2,
            2,
            0,
        ]
        self.write(step, "create_bond", args, value=STAKE)
        if key not in self.record["bonds"]:
            self.record["bonds"][key] = self.find_bond(service_name)
            self.save()
        output({"bond": key, "id": self.record["bonds"][key], "starts_at_unix": args[6]})
        return self.record["bonds"][key]

    def wait_until(self, unix: int, reason: str) -> None:
        while time.time() <= unix:
            remaining = max(0, unix - time.time())
            output({"waiting_for": reason, "seconds_remaining": round(remaining)})
            time.sleep(min(30, max(1, remaining + 1)))

    def verify_transfer(self, step: str, recipient: str, value: int) -> None:
        entry = self.record["transactions"][step]
        receipt = self.rpc("eth_getTransactionByHash", [entry["transaction_hash"]])["result"]
        children = receipt.get("triggered_transactions", [])
        if len(children) != 1:
            raise AssertionError(f"{step}: expected exactly one native transfer")
        child = self.rpc("eth_getTransactionByHash", [children[0]])["result"]
        if not child or child.get("status") != "FINALIZED" or child.get("value_credited") is not True:
            raise AssertionError(f"{step}: native transfer did not finalize and credit")
        if child.get("to_address", "").lower() != recipient.lower() or int(child.get("value", 0)) != value:
            raise AssertionError(f"{step}: native transfer recipient or value differs")
        self.record.setdefault("transfer_checks", {})[step] = {
            "checked_at": timestamp(),
            "transaction": children[0],
            "recipient": recipient,
            "value_atto": str(value),
            "status": "FINALIZED",
            "value_credited": True,
        }
        self.save()
        output({"transfer": step, "passed": True, "recipient": recipient, "value_atto": str(value)})

    def run(self) -> None:
        self.preflight()
        suffix = self.deployment["source_sha256"][:10]

        cancellation_name = f"UptimeBond cancellation acceptance {suffix}"
        cancellation_id = self.create(
            "cancellation",
            cancellation_name,
            accept_lead=300,
            start_lead=420,
        )
        self.write(
            "reject-observer-cancel",
            "cancel_offer",
            [cancellation_id],
            role="observer",
            expected_error="only the provider can cancel",
        )
        self.write("cancel-offer", "cancel_offer", [cancellation_id])
        self.assert_fields(
            "cancellation-refunded",
            self.read("get_bond", [cancellation_id]),
            {
                "status": "CANCELLED",
                "result": "PROVIDER_CANCELLED",
                "payout_recipient": self.accounts["provider"].address,
                "payout_atto": str(STAKE),
            },
        )
        self.verify_transfer("cancel-offer", self.accounts["provider"].address, STAKE)

        lifecycle_name = f"UptimeBond monitored acceptance {suffix}"
        lifecycle_id = self.create(
            "lifecycle",
            lifecycle_name,
            accept_lead=360,
            start_lead=480,
        )
        lifecycle_args = self.record["transactions"]["create-lifecycle"]["args"]
        starts_at = int(lifecycle_args[6])
        ends_at = starts_at + int(lifecycle_args[7]) * int(lifecycle_args[8])

        self.write(
            "reject-observer-readiness",
            "verify_readiness",
            [lifecycle_id],
            role="observer",
            expected_error="only the provider can verify readiness",
        )
        self.write("verify-readiness", "verify_readiness", [lifecycle_id])
        ready = self.assert_fields(
            "readiness-proven",
            self.read("get_bond", [lifecycle_id]),
            {"status": "READY"},
        )
        if (
            ready.get("readiness", {}).get("exists") is not True
            or ready["readiness"].get("http_status") != "200"
            or re.fullmatch(r"[0-9a-f]{64}", str(ready["readiness"].get("body_digest", ""))) is None
            or ready["readiness"].get("provenance") != "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH"
        ):
            raise AssertionError("Readiness provenance is incomplete")

        self.write(
            "reject-provider-accept",
            "accept_bond",
            [lifecycle_id],
            expected_error="only the beneficiary can accept",
        )
        self.write("accept-bond", "accept_bond", [lifecycle_id], role="beneficiary")
        self.assert_fields(
            "lifecycle-active",
            self.read("get_bond", [lifecycle_id]),
            {"status": "ACTIVE", "payout_recipient": "", "payout_atto": "0"},
        )

        if time.time() < starts_at:
            self.write(
                "reject-early-observation",
                "record_observation",
                [lifecycle_id],
                role="observer",
                expected_error="monitoring has not started",
            )
        self.wait_until(starts_at + 2, "first monitoring slot")
        self.write("record-slot-0", "record_observation", [lifecycle_id], role="observer")

        self.wait_until(starts_at + int(lifecycle_args[7]) + 2, "second monitoring slot")
        self.write("record-slot-1", "record_observation", [lifecycle_id], role="beneficiary")
        observations = self.read("get_observations", [lifecycle_id])
        if observations.get("total") != "2":
            raise AssertionError("Exact release did not retain both monitoring observations")
        if [item.get("slot_index") for item in observations["items"]] != ["0", "1"]:
            raise AssertionError("Monitoring observations were not stored in fixed slot order")
        for item in observations["items"]:
            if (
                item.get("result") != "PASS"
                or item.get("http_status") != "200"
                or item.get("token_present") is not True
                or item.get("body_within_limit") is not True
                or re.fullmatch(r"[0-9a-f]{64}", str(item.get("body_digest", ""))) is None
                or item.get("provenance") != "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH"
            ):
                raise AssertionError("An observation is missing strict validator provenance")
        self.record["assertions"]["validator-observations"] = {
            "checked_at": timestamp(),
            "expected": {"total": "2", "results": ["PASS", "PASS"]},
            "observed": observations,
        }
        self.save()

        self.wait_until(ends_at + 2, "monitoring end")
        self.write("finalize-bond", "finalize_bond", [lifecycle_id], role="observer")
        settled = self.assert_fields(
            "lifecycle-met",
            self.read("get_bond", [lifecycle_id]),
            {
                "status": "MET",
                "result": "SLA_MET",
                "observed_count": "2",
                "passed_count": "2",
                "failed_count": "0",
                "uptime_bps": "10000",
                "payout_recipient": self.accounts["provider"].address,
                "payout_atto": str(STAKE),
            },
        )
        self.verify_transfer("finalize-bond", self.accounts["provider"].address, STAKE)

        stats = self.read("get_stats", [])
        if (
            int(stats["total_created"]) < 2
            or int(stats["total_finalized"]) < 2
            or int(stats["total_met"]) < 1
            or stats["total_locked_atto"] != "0"
            or stats["admin_controls"] is not False
            or stats["fee_bps"] != "0"
        ):
            raise AssertionError("Final protocol accounting did not match the acceptance lifecycle")
        self.record["final_stats"] = stats
        self.record["review_bond"] = {
            "id": lifecycle_id,
            "status": settled["status"],
            "endpoint": settled["endpoint_url"],
            "readiness_digest": settled["readiness"]["body_digest"],
            "observation_count": observations["total"],
        }
        self.record["completed_at"] = timestamp()
        self.record["result"] = "PASS"
        self.save()
        output({"result": "PASS", "contract": self.address, "review_bond": lifecycle_id})


if __name__ == "__main__":
    Acceptance().run()
