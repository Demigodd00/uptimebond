# UptimeBond by demigodd00

Public-endpoint health-check bonds on GenLayer StudioNet. Test GEN has no monetary value.

- [Live app](https://uptimebond-psi.vercel.app)
- [Release and reproducible checks](docs/RELEASE.md)
- [September 10 fairness correction](docs/FAIRNESS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Steward resubmission guide](docs/SUBMISSION.md)

## How it works

A provider locks a test bond with immutable endpoint, HTTP status, proof token,
beneficiary, required check count (2–12), and failure allowance. After readiness
verification, the beneficiary accepts. Acceptance commits a pending attempt and
emits a finalized contract self-call. Each completed check queues the next.
Only the contract itself can execute checks: neither party can select, skip,
or retry an individual check.

GenLayer validators independently fetch the endpoint and require exact agreement
on status, token, response-size validity, full-body SHA-256, and outcome. No LLM
or centralized uptime reporter decides settlement.

Every planned check is required for a provider refund. Too many observed failures
pay the beneficiary. Unverifiable fetches also pay the beneficiary. If execution,
disagreement, or network delay leaves a queued check unresolved for five minutes,
any wallet can settle that committed obligation to the beneficiary. Missing
evidence is never a provider refund and is not labeled proof of an outage.

## Important scope

This is a finite sequence of network-timed consensus checkpoints, **not fixed-
interval, random, continuous, or global uptime monitoring**. Providers bear
network and evidence-availability risk as well as endpoint-compliance risk.
Both parties must accept that risk. Endpoint operators can identify or prioritize
validator traffic; this cannot establish how every ordinary client was served.
There are no admin settlement controls, protocol fees, public check retries, or
cancellation after acceptance. Unaccepted offers can be cancelled, declined, or
expired. Test-only public review fixtures are clearly distinguished from the
stable demo health endpoint.

## Run locally

Install Python dependencies from requirements-dev.txt. In apps/uptimebond-web,
copy .env.example to .env.local, then use pnpm install and pnpm dev.
Do not expose signer keys in browser environment variables.

Run the checks:

```bash
genvm-lint check contracts/uptime_bond.py
python -m pytest tests/direct/test_uptime_bond.py -q
python scripts/check_uptime_bond_release.py
```

The direct tests explicitly replay independent validator behavior. The separate
StudioNet integration test verifies autonomous child execution in the real GenVM.
The exact-address acceptance journal also checks native transfer credits, not
just transaction finality.

The September 10 release gate passed with 112 direct contract tests, 7 receipt
regressions, and 30 frontend tests. Public review cases are
[healthy ub-2](https://uptimebond-psi.vercel.app/bonds?bond=ub-2),
[HTTP-503 ub-3](https://uptimebond-psi.vercel.app/bonds?bond=ub-3), and
[unverifiable ub-4](https://uptimebond-psi.vercel.app/bonds?bond=ub-4).
The last case proves that response variance preserved the pending obligation
and paid the beneficiary after timeout. Network cancellation and transaction
finality can delay recovery beyond the evidence deadline.

New canonical contract: `0xF5E1027a28439716455F7b1778Aca17855346B87`.
Historical deployment records are retained under deployments/history.
Do not use the old 0.1 contract for the corrected submission.
