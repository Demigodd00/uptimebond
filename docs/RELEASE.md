# UptimeBond 0.2 StudioNet release

**Verification in progress:** the final response-variance lifecycle is still
running. Do not resubmit until the exact-address acceptance journal and release
gate both report PASS.

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

## Verified so far

- GenVM lint and validation passed on the concretely pinned runner.
- 112 adversarial direct tests passed, including explicit independent validator
  replay, dropped/reverted children, all failure allowances, failure suppression,
  caller-time selection attempts, ordered/duplicate checks, and single payout.
- A fresh temporary StudioNet integration deployment completed two autonomous
  checks in the real GenVM without a participant submitting either check.
- 30 frontend tests, TypeScript, and the production build passed.
- Next.js updated to 16.3.3; production dependency audit found no known vulnerabilities.
- The live app reads the exact replacement address and uses finalized-state reads.
- Review form explicitly requires evidence-risk acknowledgement.
- Cancellation ub-1 and healthy ub-2 returned and credited the full 0.001 test GEN.
- Breach ub-3 retained two HTTP 503 responses and credited 0.001 test GEN to the beneficiary.
- The acceptance journal records actual child hashes, not just UI state.

## Final release checks

Run `python scripts/check_uptime_bond_release.py`.
The gate checks source identity, committed deployment metadata, each rejection,
autonomous child execution, healthy/failed/unverifiable evidence, all four actual
native payout credits, production identity, fixture bytes, public routes, and
security headers. The acceptance script is resume-safe and uses only StudioNet.
Do not delete its journal or blindly resend transactions on a timeout.

Historical 0.1 deployment, acceptance, and hosting records are retained under
deployments/history. Do not reuse the old contract link for this correction.
