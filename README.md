# UptimeBond by demigodd00

UptimeBond is a public-endpoint performance-bond protocol deployed on GenLayer StudioNet. A provider locks test GEN for a named beneficiary against immutable endpoint terms. GenLayer validators independently fetch the endpoint in fixed monitoring slots, preserve exact response evidence, and the Intelligent Contract settles the bond from those observations.

> StudioNet GEN is test value with no monetary value. UptimeBond is not insurance, a legal service-level agreement, or continuous/global uptime monitoring.

## Verified release

| Item | Value |
|---|---|
| Live app | https://uptimebond-psi.vercel.app |
| Reviewer bond | https://uptimebond-psi.vercel.app/bonds?bond=ub-2 |
| Protocol status | https://uptimebond-psi.vercel.app/status |
| StudioNet contract | `0x308966Eb38b57798e614E3f4B4D4011C6F84367a` |
| Explorer | https://explorer-studio.genlayer.com/address/0x308966Eb38b57798e614E3f4B4D4011C6F84367a |
| Contract source SHA-256 | `d79ea8561dc7da6a1f2a28906a59b01d7b5022aa3bccb321454884c658753481` |
| Protocol fee | `0` bps |
| Admin settlement controls | None |

## Why GenLayer is essential

The web app never decides whether a service passed and cannot choose who receives the bond. During readiness and every recorded slot, GenLayer's leader and validators independently fetch the immutable public HTTPS endpoint. They require exact agreement on:

- received HTTP status;
- whether it matches the expected status;
- proof-token presence;
- response-size validity;
- the complete response SHA-256 digest; and
- the derived pass/fail result.

The contract stores those append-only receipts and applies the agreed settlement rule. Too many received failures pays the beneficiary. Enough passing observations returns the bond to the provider. Too little evidence ends inconclusive and also returns the bond. Structured evidence uses strict consensus; no LLM is added where deterministic comparison is sufficient.

## Reviewer path

1. Open the [settled reviewer bond](https://uptimebond-psi.vercel.app/bonds?bond=ub-2) without connecting a wallet.
2. Confirm `MET`, a 100% sampled result, two of two checks, zero failures, and the returned `0.001` test-GEN bond.
3. Expand **Evidence receipts**. Both slots show PASS, HTTP 200, token found, 91 bytes, and digest `846a670e1f1e66ec7e7c8e9409f966d3d0b805faaac34717a3c8da0fdc6f323d`.
4. Open [Protocol status](https://uptimebond-psi.vercel.app/status) and compare the canonical address, zero fee, no-admin flag, totals, and consensus policy with Explorer.

The full exact-address StudioNet journal is in [`deployments/uptime_bond_acceptance.json`](deployments/uptime_bond_acceptance.json). It records successful readiness, two validator observations and settlement, plus expected authorization and timing rejections. The BREACHED, INCONCLUSIVE, deadline, mutual-cancellation, and double-payment branches are covered by direct contract tests.

## Repository map

- `contracts/uptime_bond.py` — pinned-runner Intelligent Contract
- `apps/uptimebond-web` — production Next.js frontend
- `tests/direct/test_uptime_bond.py` — fast contract invariant tests
- `tests/integration/test_uptime_bond_studionet.py` — StudioNet integration coverage
- `scripts/uptimebond_acceptance.py` — resume-safe exact-address acceptance flow
- `scripts/check_uptime_bond_release.py` — local, on-chain, and hosted release gate
- `deployments/` — canonical deployment, hosting, and acceptance records
- `docs/RELEASE.md` — detailed architecture, provenance, scope, and reviewer notes

## Verify the release

Python 3.12+, Node.js 22, pnpm 11.19.0, and the pinned packages in `requirements-dev.txt` and `requirements-deploy.txt` are expected.

```bash
python -m pip install -r requirements-deploy.txt
python scripts/check_uptime_bond_release.py
```

The frontend can also be checked independently:

```bash
cd apps/uptimebond-web
pnpm install --frozen-lockfile
pnpm test
pnpm typecheck
pnpm build
pnpm audit:prod
```

Never place a private key in frontend environment variables. Browser transactions are signed by the user's injected wallet. Real StudioNet write scripts require `UPTIMEBOND_PRIVATE_KEY` only in the operator's uncommitted root `.env` or process environment.

## Evidence boundary

UptimeBond proves the exact endpoint response on the recorded samples. It does not prove service ownership, continuous availability between slots, low latency, or reachability from every region. Transport failures record no observation and can be retried; missing evidence becomes `INCONCLUSIVE` instead of invented downtime.

## Ownership and license

UptimeBond was created by **demigodd00**. Copyright © 2026 demigodd00. All rights reserved. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). Public source visibility does not grant permission to copy, republish, rebrand, or claim this work as someone else's.
