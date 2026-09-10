"""Run UptimeBond's repeatable local, on-chain, and hosted release gate."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "uptime_bond.py"
DIRECT_TEST_PATH = ROOT / "tests" / "direct" / "test_uptime_bond.py"
DEPLOY_SCRIPT_PATH = ROOT / "scripts" / "deploy_uptime_bond.py"
ACCEPTANCE_SCRIPT_PATH = ROOT / "scripts" / "uptimebond_acceptance.py"
INTEGRATION_TEST_PATH = ROOT / "tests" / "integration" / "test_uptime_bond_studionet.py"
DEPLOYMENT_PATH = ROOT / "deployments" / "uptime_bond_studionet.json"
ACCEPTANCE_PATH = ROOT / "deployments" / "uptime_bond_acceptance.json"
HOSTING_PATH = ROOT / "deployments" / "uptime_bond_vercel.json"
WEB_PATH = ROOT / "apps" / "uptimebond-web"
RPC_URL = "https://studio.genlayer.com/api"
ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_ADDRESS = "0xF5E1027a28439716455F7b1778Aca17855346B87"
EXPECTED_FIXTURE_DIGEST = "846a670e1f1e66ec7e7c8e9409f966d3d0b805faaac34717a3c8da0fdc6f323d"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-web-build", action="store_true")
    parser.add_argument("--skip-live", action="store_true")
    return parser.parse_args()


def run_check(label: str, command: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n[{label}]")
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(command, cwd=cwd, check=False, env=environment)
    print(f"{'PASS' if result.returncode == 0 else 'FAIL'}: {label}")
    return result.returncode == 0


def source_digest() -> str:
    source = CONTRACT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def frontend_address() -> str:
    for path in (
        WEB_PATH / ".env.production.local",
        WEB_PATH / ".env.local",
        WEB_PATH / ".env.example",
    ):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("NEXT_PUBLIC_UPTIMEBOND_ADDRESS="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("NEXT_PUBLIC_UPTIMEBOND_ADDRESS", "").strip()


def load_records() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (DEPLOYMENT_PATH, ACCEPTANCE_PATH, HOSTING_PATH)
    )  # type: ignore[return-value]


def verify_records() -> tuple[bool, dict | None, dict | None]:
    print("\n[release records and acceptance provenance]")
    try:
        deployment, acceptance, hosting = load_records()
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: release records cannot be read: {error}")
        return False, None, None

    address = str(deployment.get("address", ""))
    transactions = acceptance.get("transactions", {})
    assertions = acceptance.get("assertions", {})
    transfer_checks = acceptance.get("transfer_checks", {})
    autonomous = acceptance.get("autonomous_checks", {})
    required_steps = {"create-cancellation", "reject-observer-cancel", "cancel-offer", "reject-provider-accept"}
    for case in ("lifecycle", "breach", "variance"):
        required_steps.update({f"create-{case}", f"ready-{case}", f"accept-{case}", f"reject-repeat-settlement-{case}"})
        required_steps.update(f"reject-manual-{case}-{role}" for role in ("provider", "beneficiary", "observer"))
    checks = {
        "contract identity and StudioNet release": deployment.get("contract") == "UptimeBond"
        and deployment.get("network") == "studionet" and deployment.get("version") == "0.2.0-studionet",
        "canonical address": address == EXPECTED_ADDRESS and ADDRESS_PATTERN.fullmatch(address) is not None,
        "validated source digest": deployment.get("source_sha256") == source_digest(),
        "mandatory preflight and successful deployment": deployment.get("preflight_skipped") is False
        and deployment.get("receipt_status") == "FINALIZED" and deployment.get("execution_result") == "SUCCESS"
        and deployment.get("verified_source_and_config") is True,
        "concrete pinned runner": str(deployment.get("runner_dependency", "")).startswith('# { "Depends": "py-genlayer:')
        and "latest" not in str(deployment.get("runner_dependency", "")) and "test" not in str(deployment.get("runner_dependency", "")),
        "frontend exact address": frontend_address().lower() == address.lower(),
        "acceptance exact source and address": acceptance.get("contract") == address
        and acceptance.get("source_sha256") == deployment.get("source_sha256"),
        "acceptance completed": acceptance.get("result") == "PASS",
        "all writes verified, rejections stayed failures": all(
            transactions.get(step, {}).get("checked") is True
            and transactions.get(step, {}).get("execution_succeeded") is (not step.startswith("reject-"))
            for step in required_steps),
        "no wallet submitted a successful check": all(
            not (entry.get("method") == "record_observation" and entry.get("execution_succeeded") is True)
            for entry in transactions.values()),
        "no fees, admins, or locked acceptance funds": acceptance.get("final_stats", {}).get("fee_bps") == "0"
        and acceptance.get("final_stats", {}).get("admin_controls") is False
        and acceptance.get("final_stats", {}).get("total_locked_atto") == "0",
        "missing evidence risk belongs to provider": acceptance.get("final_stats", {}).get("missing_evidence_payout") == "BENEFICIARY"
        and acceptance.get("final_stats", {}).get("sampling_policy") == "AUTONOMOUS_FINALIZED_SELF_CALLS",
        "hosting points to replacement": hosting.get("contract_address") == address and hosting.get("ready_state") == "READY"
        and hosting.get("target") == "production" and hosting.get("health_verified") is True,
        "stable hosted demo fixture": hosting.get("fixture_status") == 200
        and hosting.get("fixture_bytes") == 91 and hosting.get("fixture_sha256") == EXPECTED_FIXTURE_DIGEST,
    }
    for case, status, role in (("lifecycle", "MET", "provider"), ("breach", "BREACHED", "beneficiary"), ("variance", "UNVERIFIABLE", "beneficiary")):
        result = assertions.get(f"{case}-settled", {}).get("observed", {})
        recipient = acceptance.get("wallets", {}).get(role)
        transfer = transfer_checks.get(f"payout-{case}", transfer_checks.get(f"timeout-{case}", {}))
        checks[f"{case}: correct terminal status and recipient"] = result.get("status") == status and result.get("payout_recipient") == recipient
        checks[f"{case}: whole test bond actually credited"] = result.get("payout_atto") == str(10**15) and transfer.get("value_credited") is True and transfer.get("recipient") == recipient and transfer.get("value_atto") == str(10**15)
        observations = assertions.get(f"{case}-observations", {}).get("observed", {}).get("items", [])
        if case != "variance":
            children = autonomous.get(case, [])
            checks[f"{case}: two real finalized self-calls"] = len(children) == 2 and all(
                c.get("sender", "").lower() == address.lower() and c.get("recipient", "").lower() == address.lower()
                and c.get("status") == "FINALIZED" and c.get("execution_succeeded") is True for c in children)
            checks[f"{case}: all required observations"] = len(observations) == 2 and [o.get("slot_index") for o in observations] == ["0", "1"]
            checks[f"{case}: strict independent provenance"] = bool(observations) and all(
                DIGEST_PATTERN.fullmatch(str(o.get("body_digest", ""))) is not None
                and o.get("provenance") == "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH" for o in observations)
        if case == "lifecycle":
            checks["healthy fixture evidence unchanged"] = all(o.get("result") == "PASS" and o.get("body_digest") == EXPECTED_FIXTURE_DIGEST for o in observations)
        elif case == "breach":
            checks["actual received failure demonstrated"] = any(o.get("result") == "FAIL_STATUS" and o.get("http_status") == "503" for o in observations)
        else:
            attempt = acceptance.get("unverifiable_attempts", {}).get(case, {})
            checks["response variance did not erase the parent obligation"] = attempt.get("child_execution_succeeded") is False and attempt.get("committed_state", {}).get("status") == "ACTIVE" and any(o.get("result") == "PENDING" for o in attempt.get("observations_before_timeout", {}).get("items", []))
            checks["unverifiable record is not fabricated outage evidence"] = any(o.get("result") == "UNVERIFIABLE_TIMEOUT" and o.get("body_digest") == "" and o.get("observed_at_unix") == "0" for o in observations)
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {label}")
    return all(checks.values()), deployment, hosting


def request(url: str) -> tuple[int, bytes, dict[str, str]]:
    req = Request(url, headers={"User-Agent": "UptimeBond-release-gate/1.0"})
    with urlopen(req, timeout=30) as response:
        return response.status, response.read(), {key.lower(): value for key, value in response.headers.items()}


def rpc(method: str, params: list) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = Request(
        RPC_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "UptimeBond-release-gate/1.0"},
    )
    with urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(str(payload["error"]))
    return payload


def verify_live(deployment: dict | None, hosting: dict | None) -> bool:
    print("\n[live StudioNet and production checks]")
    if not deployment or not hosting:
        print("FAIL: verified release records are unavailable")
        return False
    try:
        address = deployment["address"]
        code = base64.b64decode(rpc("gen_getContractCode", [address])["result"], validate=True)
        live_source_digest = hashlib.sha256(code.replace(b"\r\n", b"\n")).hexdigest()
        base_url = str(hosting["production_url"]).rstrip("/")
        health_status, health_body, health_headers = request(base_url + "/api/health")
        health = json.loads(health_body.decode("utf-8"))
        fixture_status, fixture_body, _ = request(base_url + "/api/demo-health")
        page_results = {path: request(base_url + path)[0] for path in ("/", "/bonds?bond=ub-2", "/bonds/new", "/how-it-works", "/status")}
        acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        live_transfers = []
        for transfer in acceptance.get("transfer_checks", {}).values():
            time.sleep(2.25)
            receipt = rpc("eth_getTransactionByHash", [transfer["transaction"]])["result"]
            live_transfers.append(bool(receipt) and receipt.get("status") == "FINALIZED"
                                 and receipt.get("value_credited") is True
                                 and receipt.get("to_address", "").lower() == transfer["recipient"].lower()
                                 and str(receipt.get("value")) == transfer["value_atto"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(f"FAIL: live verification failed: {error}")
        return False
    headers = {key.lower(): value for key, value in health_headers.items()}
    checks = {
        "all four native payout credits still verifiable on-chain": len(live_transfers) == 4 and all(live_transfers),
        "on-chain source still exact": live_source_digest == deployment.get("source_sha256"),
        "health endpoint identifies release": health_status == 200
        and health.get("product") == "UptimeBond"
        and health.get("release") == "0.2.0"
        and health.get("network") == "StudioNet"
        and health.get("samplingPolicy") == "AUTONOMOUS_FINALIZED_SELF_CALLS"
        and health.get("missingEvidencePayout") == "BENEFICIARY",
        "health endpoint exact contract": str(health.get("contractAddress", "")).lower()
        == str(deployment.get("address", "")).lower(),
        "health endpoint release-ready": health.get("readyForStudioNetTesting") is True
        and health.get("adminSettlement") is False
        and health.get("feeBps") == 0,
        "public fixture remains immutable": fixture_status == 200
        and len(fixture_body) == 91
        and hashlib.sha256(fixture_body).hexdigest() == EXPECTED_FIXTURE_DIGEST,
        "all reviewer routes respond": all(status == 200 for status in page_results.values()),
        "anti-framing header": headers.get("x-frame-options") == "DENY",
        "content sniffing blocked": headers.get("x-content-type-options") == "nosniff",
        "browser permissions restricted": "camera=()" in headers.get("permissions-policy", "")
        and "microphone=()" in headers.get("permissions-policy", "")
        and "geolocation=()" in headers.get("permissions-policy", ""),
        "framing CSP restricted": "frame-ancestors 'none'" in headers.get("content-security-policy", ""),
    }
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {label}")
    return all(checks.values())


def main() -> int:
    options = parse_args()
    results = [
        run_check("GenVM lint and validation", ["genvm-lint", "check", str(CONTRACT_PATH)]),
        run_check("direct contract tests", [sys.executable, "-m", "pytest", str(DIRECT_TEST_PATH), "-q"]),
        run_check(
            "release script compilation",
            [
                sys.executable,
                "-m",
                "py_compile",
                str(DEPLOY_SCRIPT_PATH),
                str(ACCEPTANCE_SCRIPT_PATH),
                str(INTEGRATION_TEST_PATH),
                str(ROOT / "scripts" / "cache_genvm_runners.py"),
                str(Path(__file__)),
            ],
        ),
    ]
    if not options.skip_web_build:
        pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
        if pnpm is None:
            print("\nFAIL: pnpm is not installed")
            results.append(False)
        else:
            results.extend(
                [
                    run_check("web tests", [pnpm, "test"], WEB_PATH),
                    run_check("web typecheck", [pnpm, "typecheck"], WEB_PATH),
                    run_check("web production build", [pnpm, "build"], WEB_PATH),
                    run_check(
                        "web production dependency audit",
                        [pnpm, "audit", "--prod", "--audit-level=high"],
                        WEB_PATH,
                    ),
                ]
            )
    records_ok, deployment, hosting = verify_records()
    results.append(records_ok)
    if not options.skip_live:
        results.append(verify_live(deployment, hosting))
    print("\nUptimeBond release gate: " + ("PASS" if all(results) else "FAIL"))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
