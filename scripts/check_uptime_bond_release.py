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
EXPECTED_ADDRESS = "0x308966Eb38b57798e614E3f4B4D4011C6F84367a"
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
    observations = assertions.get("validator-observations", {}).get("observed", {})
    observation_items = observations.get("items", []) if isinstance(observations, dict) else []
    readiness = assertions.get("readiness-proven", {}).get("observed", {}).get("readiness", {})
    cancellation = assertions.get("cancellation-refunded", {}).get("observed", {})
    settled = assertions.get("lifecycle-met", {}).get("observed", {})
    transfer_checks = acceptance.get("transfer_checks", {})
    required_steps = {
        "create-cancellation",
        "reject-observer-cancel",
        "cancel-offer",
        "create-lifecycle",
        "reject-observer-readiness",
        "verify-readiness",
        "reject-provider-accept",
        "accept-bond",
        "reject-early-observation",
        "record-slot-0",
        "record-slot-1",
        "finalize-bond",
    }
    rejected_steps = {
        "reject-observer-cancel",
        "reject-observer-readiness",
        "reject-provider-accept",
        "reject-early-observation",
    }
    positive_steps = required_steps - rejected_steps
    checks = {
        "contract identity": deployment.get("contract") == "UptimeBond",
        "StudioNet network": deployment.get("network") == "studionet",
        "canonical address": address.lower() == EXPECTED_ADDRESS.lower()
        and ADDRESS_PATTERN.fullmatch(address) is not None,
        "validated source digest": deployment.get("source_sha256") == source_digest(),
        "preflight was mandatory": deployment.get("preflight_skipped") is False,
        "deployment execution succeeded": deployment.get("receipt_status") == "FINALIZED"
        and deployment.get("execution_result") == "SUCCESS",
        "deployed source and config verified": deployment.get("verified_source_and_config") is True,
        "pinned runner": str(deployment.get("runner_dependency", "")).startswith(
            '# { "Depends": "py-genlayer:'
        )
        and "latest" not in str(deployment.get("runner_dependency", ""))
        and "test" not in str(deployment.get("runner_dependency", "")),
        "frontend exact address": frontend_address().lower() == address.lower(),
        "acceptance exact address": str(acceptance.get("contract", "")).lower() == address.lower(),
        "acceptance exact source": acceptance.get("source_sha256") == deployment.get("source_sha256"),
        "acceptance passed": acceptance.get("result") == "PASS",
        "all acceptance steps recorded": required_steps.issubset(transactions)
        and all(transactions[step].get("checked") is True for step in required_steps),
        "expected rejections stayed failures": all(
            transactions[step].get("execution_succeeded") is False for step in rejected_steps
        ),
        "positive lifecycle writes executed": all(
            transactions[step].get("execution_succeeded") is True for step in positive_steps
        ),
        "readiness evidence fingerprinted": readiness.get("exists") is True
        and readiness.get("http_status") == "200"
        and readiness.get("body_bytes") == "91"
        and readiness.get("body_digest") == EXPECTED_FIXTURE_DIGEST
        and readiness.get("provenance") == "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH",
        "two append-only slot observations": observations.get("total") == "2"
        and [item.get("slot_index") for item in observation_items] == ["0", "1"],
        "observation decisions and provenance": len(observation_items) == 2
        and all(
            item.get("result") == "PASS"
            and item.get("http_status") == "200"
            and item.get("token_present") is True
            and item.get("body_within_limit") is True
            and item.get("body_digest") == EXPECTED_FIXTURE_DIGEST
            and DIGEST_PATTERN.fullmatch(str(item.get("body_digest", ""))) is not None
            and item.get("provenance") == "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH"
            for item in observation_items
        ),
        "cancelled offer refunded": cancellation.get("status") == "CANCELLED"
        and cancellation.get("payout_atto") == str(10**15)
        and transfer_checks.get("cancel-offer", {}).get("value_credited") is True,
        "monitored bond settled MET": settled.get("status") == "MET"
        and settled.get("result") == "SLA_MET"
        and settled.get("observed_count") == "2"
        and settled.get("uptime_bps") == "10000",
        "final payout credited": transfer_checks.get("finalize-bond", {}).get("value_credited") is True
        and transfer_checks.get("finalize-bond", {}).get("value_atto") == str(10**15),
        "zero fee and no admin": acceptance.get("final_stats", {}).get("fee_bps") == "0"
        and acceptance.get("final_stats", {}).get("admin_controls") is False,
        "nothing remains locked": acceptance.get("final_stats", {}).get("total_locked_atto") == "0",
        "hosting exact address": str(hosting.get("contract_address", "")).lower() == address.lower(),
        "hosting release is ready": hosting.get("ready_state") == "READY"
        and hosting.get("target") == "production"
        and hosting.get("health_verified") is True,
        "hosted fixture is exact": hosting.get("fixture_status") == 200
        and hosting.get("fixture_bytes") == 91
        and hosting.get("fixture_sha256") == EXPECTED_FIXTURE_DIGEST,
    }
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
    except (OSError, KeyError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(f"FAIL: live verification failed: {error}")
        return False
    headers = {key.lower(): value for key, value in health_headers.items()}
    checks = {
        "on-chain source still exact": live_source_digest == deployment.get("source_sha256"),
        "health endpoint identifies release": health_status == 200
        and health.get("product") == "UptimeBond"
        and health.get("release") == "0.1.0"
        and health.get("network") == "StudioNet",
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
