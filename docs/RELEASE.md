# UptimeBond StudioNet release

UptimeBond by demigodd00 is a public-endpoint performance-bond protocol for GenLayer StudioNet. StudioNet GEN is test value with no monetary value.

## Release identity

| Item | Release value |
|---|---|
| Live app | https://uptimebond-psi.vercel.app |
| Reviewer bond | https://uptimebond-psi.vercel.app/bonds?bond=ub-2 |
| Read-only status | https://uptimebond-psi.vercel.app/status |
| Contract | `0x308966Eb38b57798e614E3f4B4D4011C6F84367a` |
| Explorer | https://explorer-studio.genlayer.com/address/0x308966Eb38b57798e614E3f4B4D4011C6F84367a |
| Deployment transaction | `0x6955a33c29a73aa30a5efb321b116b029f23769c4e6c31310b4a9c07aeb6fd05` |
| Contract source SHA-256 | `d79ea8561dc7da6a1f2a28906a59b01d7b5022aa3bccb321454884c658753481` |
| Web deployment | `dpl_2pbzUsnnBL7aZGFDUGuRUFt19EKA` |
| Validator fixture SHA-256 | `846a670e1f1e66ec7e7c8e9409f966d3d0b805faaac34717a3c8da0fdc6f323d` |
| Protocol fee | `0` basis points |
| Admin settlement controls | None |

Machine-readable deployment, acceptance, and hosting records are in [`deployments/uptime_bond_studionet.json`](../deployments/uptime_bond_studionet.json), [`deployments/uptime_bond_acceptance.json`](../deployments/uptime_bond_acceptance.json), and [`deployments/uptime_bond_vercel.json`](../deployments/uptime_bond_vercel.json).

## Why this is GenLayer-native

The frontend does not report uptime or choose a payout. A provider signs immutable terms and locks test GEN for a named beneficiary. GenLayer validators independently fetch the public HTTPS endpoint during readiness and each fixed monitoring slot. The contract requires exact agreement on the received HTTP status, expected-status match, proof-token presence, response-size validity, complete response SHA-256 digest, and derived result.

Those consensus results are append-only settlement evidence. After the final slot, the Intelligent Contract applies the agreed rule: too many received failures pays the beneficiary; enough passing observations returns the bond to the provider; too little evidence ends `INCONCLUSIVE` and returns the bond. There is no owner verdict, admin payout method, fee withdrawal, or centralized escrow operator. Structured evidence is handled with strict comparison; an LLM would add uncertainty without adding useful judgment.

## Evidence provenance

The signed creation transaction binds the provider wallet to the endpoint, expected status, proof token, beneficiary, schedule, and thresholds. Readiness then proves that GenLayer validators independently received the agreed token and response before the beneficiary accepted. Every observation stores its fixed slot, result, HTTP status, token/status checks, byte count, full body digest, validator provenance label, and contract time.

This record proves which endpoint response validators agreed on at each sampled check. It does not prove legal ownership of a domain, authorship of endpoint content, continuous availability between slots, low latency, or availability from every region. Transport failures do not fabricate downtime; they produce no observation and may be retried. Missing evidence is surfaced as `INCONCLUSIVE`, never silently treated as uptime.

## User and owner boundaries

- The provider creates an offer, locks the complete test bond, verifies readiness, and may cancel only before acceptance.
- The named beneficiary may accept or decline after readiness.
- Any wallet may record one observation per open slot and finalize after monitoring ends.
- Active cancellation requires matching consent from both participants.
- The deployer has no special contract role after deployment.
- The UI previews eligibility and progress, but the contract independently enforces roles, time windows, value, and settlement.

## Exact-address acceptance

The canonical release was exercised with provider, beneficiary, and independent observer wallets:

- deployed source and release configuration matched the recorded local contract;
- an observer could not cancel a provider offer;
- provider cancellation returned and credited the complete `0.001` test-GEN bond;
- an observer could not perform provider readiness;
- validators independently fetched the 91-byte HTTPS fixture and stored digest `846a670e…6f323d`;
- the provider could not accept its own bond; the named beneficiary activated it;
- an observation before monitoring started was rejected;
- observer and beneficiary wallets recorded passing observations in slots 0 and 1;
- both receipts preserved HTTP 200, token present, body within limit, 91 bytes, and the full matching digest;
- an observer finalized reviewer bond `ub-2` as `MET` with 2/2 passing observations;
- the complete `0.001` test-GEN bond was credited back to the provider; and
- final accounting showed two created and finalized bonds, one `MET`, zero locked value, zero fees, and no admin controls.

The failure, insufficient-evidence, deadline, authorization, mutual-cancellation, and double-payment branches are covered by 29 direct contract tests. The exact-address acceptance deliberately uses a stable passing fixture; it does not misrepresent a simulated outage as a live public failure.

## Reviewer path

1. Open https://uptimebond-psi.vercel.app/bonds?bond=ub-2 without connecting a wallet.
2. Confirm `MET`, 100% sampled result, 2 of 2 checks, zero failures, and the returned `0.001` test-GEN bond.
3. Expand **Evidence receipts** and compare both fixed-slot records and their complete SHA-256 digests.
4. Open https://uptimebond-psi.vercel.app/status and compare the canonical address, zero fee, no-admin flag, totals, and consensus policy with Explorer.

## Repeat the release gate

```bash
python scripts/check_uptime_bond_release.py
```

The gate reruns GenVM validation, 29 direct contract tests, 27 frontend tests, TypeScript, the production build, the production dependency audit, deployment/acceptance provenance checks, live on-chain source hashing, hosted fixture hashing, route checks, and security-header checks.

`scripts/uptimebond_acceptance.py` performs real StudioNet writes and is resume-safe. Its completed journal should not be deleted or rerun casually.

## Scope

This is a StudioNet demonstration, not an insurance product, legal service-level agreement, continuous monitoring service, or mainnet security claim. It supports public, non-sensitive, static UTF-8 health responses no larger than 16 KB. A keeper or participant must trigger each slot because Intelligent Contracts do not schedule their own transactions.
