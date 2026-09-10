"""Preflight, deploy, verify, and record the canonical UptimeBond release.

Environment:
    UPTIMEBOND_PRIVATE_KEY   required signer key
    UPTIMEBOND_NETWORK       studionet (default) | localnet

The script will never generate a replacement key. If a submitted deployment
times out, rerun with --resume-transaction and the printed transaction hash.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from eth_utils import to_checksum_address
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import localnet, studionet
from genlayer_py.types import TransactionHashVariant, TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
CODE_PATH = ROOT / "contracts" / "uptime_bond.py"
TEST_PATH = ROOT / "tests" / "direct" / "test_uptime_bond.py"
DEPLOYMENTS_DIR = ROOT / "deployments"
ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
TX_PATTERN = re.compile(r"^0x[0-9a-fA-F]{64}$")
VERSION = "0.2.0-studionet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resume-transaction",
        help="Verify an already-submitted deployment instead of deploying again",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Local debugging only; release deployment records must never use this",
    )
    return parser.parse_args()


def run_preflight() -> None:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    subprocess.run(
        ["genvm-lint", "check", str(CODE_PATH)],
        cwd=ROOT,
        check=True,
        env=environment,
    )
    subprocess.run(
        [sys.executable, "-m", "pytest", str(TEST_PATH), "-q"],
        cwd=ROOT,
        check=True,
        env=environment,
    )


def source_digest(code: str) -> str:
    return hashlib.sha256(code.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def assert_success(receipt: dict) -> None:
    if receipt.get("error"):
        raise RuntimeError(f"deployment failed: {receipt['error']}")
    status = receipt.get("status_name") or receipt.get("statusName")
    if status != TransactionStatus.FINALIZED.value:
        raise RuntimeError("deployment did not reach FINALIZED status")
    if not tx_execution_succeeded(receipt):
        consensus = receipt.get("consensus_data", {})
        leaders = consensus.get("leader_receipt", []) if isinstance(consensus, dict) else []
        if isinstance(leaders, dict):
            leaders = [leaders]
        detail = ""
        if isinstance(leaders, list) and leaders and isinstance(leaders[0], dict):
            detail = str(leaders[0].get("genvm_result") or leaders[0].get("execution_result") or "")
        raise RuntimeError(
            "deployment finalized without successful contract execution"
            + (f": {detail[:500]}" if detail else "")
        )


def extract_address(receipt: dict) -> str:
    for key in ("tx_data_decoded", "data"):
        value = receipt.get(key)
        if isinstance(value, dict) and value.get("contract_address"):
            address = str(value["contract_address"])
            if ADDRESS_PATTERN.fullmatch(address) is None or int(address[2:], 16) == 0:
                raise RuntimeError("deployment receipt contained an invalid contract address")
            return to_checksum_address(address)
    raise RuntimeError("finalized deployment receipt did not contain a contract address")


def verify_source(client, address: str, expected_code: str) -> str:
    response = client.provider.make_request(method="gen_getContractCode", params=[address])
    encoded = response.get("result")
    if not isinstance(encoded, str):
        raise RuntimeError("could not retrieve deployed source")
    try:
        deployed = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeError):
        raise RuntimeError("deployed source was not valid base64-encoded Python") from None
    digest = source_digest(expected_code)
    if source_digest(deployed) != digest:
        raise RuntimeError("deployed source differs from the validated local source")
    return digest


def verify_configuration(client, address: str, account) -> dict:
    stats = client.read_contract(
        address=address,
        function_name="get_stats",
        args=[],
        account=account,
        transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
    )
    expected = {
        "fee_bps": "0",
        "admin_controls": False,
        "experimental": True,
        "max_page_size": "25",
        "max_response_bytes": "16000",
        "probe_policy": "STRICT_INDEPENDENT_STATUS_TOKEN_SIZE_AND_SHA256",
        "sampling_policy": "AUTONOMOUS_FINALIZED_SELF_CALLS",
        "evidence_risk_bearer": "PROVIDER",
        "missing_evidence_payout": "BENEFICIARY",
        "check_timeout_secs": "300",
        "version": VERSION,
        "total_created": "0",
        "total_finalized": "0",
        "total_locked_atto": "0",
    }
    if not isinstance(stats, dict) or any(stats.get(key) != value for key, value in expected.items()):
        raise RuntimeError("deployed configuration does not match the release")
    return stats


def record_deployment(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        previous_address = str(previous.get("address", ""))
        if previous_address.lower() != str(record["address"]).lower():
            history = path.parent / "history"
            history.mkdir(exist_ok=True)
            history_path = history / f"{path.stem}_{previous_address[2:].lower()}.json"
            if history_path.exists():
                if json.loads(history_path.read_text(encoding="utf-8")) != previous:
                    raise RuntimeError("deployment history differs; refusing to overwrite it")
            else:
                history_path.write_text(json.dumps(previous, indent=2) + "\n", encoding="utf-8")
            record["previous_address"] = previous_address
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix="uptimebond-record-",
        suffix=".json.tmp",
        delete=False,
    ) as temporary:
        json.dump(record, temporary, indent=2)
        temporary.write("\n")
        pending = Path(temporary.name)
    pending.replace(path)


def main() -> None:
    args = parse_args()
    network_name = os.environ.get("UPTIMEBOND_NETWORK", "studionet").strip().lower()
    chains = {"studionet": studionet, "localnet": localnet}
    if network_name not in chains:
        raise ValueError("UPTIMEBOND_NETWORK must be studionet or localnet")
    if args.resume_transaction and TX_PATTERN.fullmatch(args.resume_transaction) is None:
        raise ValueError("--resume-transaction must be a 32-byte transaction hash")

    private_key = os.environ.get("UPTIMEBOND_PRIVATE_KEY", "").strip()
    if not private_key:
        raise RuntimeError("UPTIMEBOND_PRIVATE_KEY is required; no key will be generated")
    if not args.skip_preflight:
        run_preflight()

    code = CODE_PATH.read_text(encoding="utf-8")
    account = Account.from_key(private_key)
    client = create_client(chain=chains[network_name], account=account)
    print(
        f"network={network_name} deployer={account.address} source_sha256={source_digest(code)}",
        flush=True,
    )
    if args.resume_transaction:
        tx_hash = args.resume_transaction
        print(f"resuming_transaction={tx_hash}", flush=True)
    else:
        tx_hash = client.deploy_contract(code=code, account=account, args=[])
        print(f"transaction={tx_hash}", flush=True)

    receipt = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        status=TransactionStatus.FINALIZED,
        interval=3000,
        retries=120,
        full_transaction=True,
    )
    assert_success(receipt)
    address = extract_address(receipt)
    digest = verify_source(client, address, code)
    stats = verify_configuration(client, address, account)
    record = {
        "contract": "UptimeBond",
        "version": VERSION,
        "network": network_name,
        "address": address,
        "transaction_hash": str(tx_hash),
        "deployer": account.address,
        "deployer_role": "deployment_only_no_admin_controls_or_protocol_fees",
        "constructor_args": [],
        "source_sha256": digest,
        "runner_dependency": code.splitlines()[0],
        "preflight_skipped": args.skip_preflight,
        "receipt_status": "FINALIZED",
        "execution_result": "SUCCESS",
        "verified_source_and_config": True,
        "deployed_stats": stats,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    }
    output_path = DEPLOYMENTS_DIR / f"uptime_bond_{network_name}.json"
    record_deployment(output_path, record)
    print(f"verified_deployment={address}", flush=True)
    print(f"record={output_path}", flush=True)


if __name__ == "__main__":
    main()
