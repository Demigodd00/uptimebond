# UptimeBond 0.2 StudioNet release

**Verified on September 10, 2026:** exact-address acceptance and the full release
gate both passed. The live app uses this replacement contract. This is evidence
for a StudioNet resubmission, not a guarantee of steward approval or mainnet safety.

## Identity

- App: https://uptimebond-psi.vercel.app
- Repository: https://github.com/Demigodd00/uptimebond
- Contract: `0xF5E1027a28439716455F7b1778Aca17855346B87`
- Explorer: https://explorer-studio.genlayer.com/address/0xF5E1027a28439716455F7b1778Aca17855346B87
- Source SHA-256: `415f9ee2d28da8a99e97b99d5fcde19680a5739a7cb0f41071c5a368e7f7b40f`
- Deployment transaction: `0x1ccc572d6441ea304d62e821c1a06f51ad75202f1aadc4d537d1fd6bfb25804f`
- Current hosting record: deployments/uptime_bond_vercel.json.

## Steward correction

The original review was valid: manually timed checks and provider refunds for
insufficient evidence let evidence suppression improve the provider's outcome.

Acceptance now commits a pending obligation and emits a finalized self-call.
Only the contract can execute individual checks. Each completed check commits
and queues the next. Every agreed check is required. Missing or unverifiable
evidence pays the beneficiary under explicit evidence-risk terms, including
network faults. Public retries and active cancellation were removed. Parent
state survives failed child execution.

See the fairness note and architecture for the exact state machine and trust
boundaries. These are finite finality-driven checkpoints, not fixed-interval,
random, global, or continuous uptime monitoring. Test GEN is valueless.

## Verified results

- GenVM lint and validation passed on the concretely pinned runner.
- 112 adversarial direct tests passed, including explicit independent validator
  replay, dropped/reverted children, all failure allowances, failure suppression,
  caller-time selection attempts, ordered/duplicate checks, and single payout.
- A fresh temporary StudioNet integration deployment completed two autonomous
  checks in the real GenVM without a participant submitting either check.
- 7 receipt-finality regression tests passed. Leader execution success alone is
  never counted as a committed observation.
- 30 frontend tests, TypeScript, and the production build passed.
- Next.js updated to 16.3.3; production dependency audit found no known vulnerabilities.
- The live app reads the exact replacement address and uses finalized-state reads.
- Review form explicitly requires evidence-risk acknowledgement.
- Cancellation ub-1 and healthy ub-2 returned and credited the full 0.001 test GEN.
- Breach ub-3 retained two HTTP 503 responses and credited 0.001 test GEN to the beneficiary.
- Variance ub-4 preserved its pending attempt after the disagreeing child was
  canceled by StudioNet. The provider's timeout call finalized UNVERIFIABLE and
  credited the full 0.001 test GEN to the beneficiary, not the provider.
- The acceptance journal records actual child hashes, not just UI state.
- All four acceptance bonds settled; 0.002 test GEN was credited to the provider,
  0.002 to the beneficiary, and zero acceptance funds remained locked.
- The complete release gate passed: lint, 112 direct tests, 7 receipt tests,
  30 frontend tests, typecheck, build, dependency audit, source and address
  identity, live payout credits, public routes, and security headers.

## Reproduce the review without signing

| Bond | Public evidence | Verified result |
| --- | --- | --- |
| [ub-2](https://uptimebond-psi.vercel.app/bonds?bond=ub-2) | Two independently verified stable responses | MET; provider credited 0.001 test GEN |
| [ub-3](https://uptimebond-psi.vercel.app/bonds?bond=ub-3) | Two independently verified HTTP 503 responses | BREACHED; beneficiary credited 0.001 test GEN |
| [ub-4](https://uptimebond-psi.vercel.app/bonds?bond=ub-4) | Committed attempt, canceled disagreeing child, timeout receipt | UNVERIFIABLE; beneficiary credited 0.001 test GEN |

The response-variance child is
`0xd67e6c03ca0da3075e8afef789a5a8eadec737e4d00a39b05b659f378c64a4be`.
It had a successful leader execution but a CANCELED transaction status; no
observation committed. Do not confuse leader success with consensus finality.
The timeout settlement is
`0x83aa91cf32b4fc37e22c7bf1e59947953f3efd5fbdc38dc09b094e0f1d802244`.
The verified beneficiary native credit is
`0xf07be05fe060171acc630808d4e578f9ab97c3ceab0cfe7bd73986f48278c998`.

StudioNet held the disagreeing child in consensus before canceling it. Recovery
then completed. The five-minute evidence deadline determines eligibility, not
guaranteed execution time. Timeout settlement still needs a transaction and
network progress; the provider bears this disclosed evidence-availability risk.

## Final release checks

Run `python scripts/check_uptime_bond_release.py`.
The gate checks source identity, committed deployment metadata, each rejection,
autonomous child execution, healthy/failed/unverifiable evidence, all four actual
native payout credits, production identity, fixture bytes, public routes, and
security headers. The acceptance script is resume-safe and uses only StudioNet.
Do not delete its journal or blindly resend transactions on a timeout.

Historical 0.1 deployment, acceptance, and hosting records are retained under
deployments/history. Do not reuse the old contract link for this correction.
