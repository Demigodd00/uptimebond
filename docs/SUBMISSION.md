# UptimeBond — steward resubmission

Use **Edit / Resubmit on the existing contribution**, not a duplicate new contribution.
Replace every old 0.1 contract or pinned-source link. Keep the website and dedicated
GitHub repository. The exact-address acceptance journal and full release gate
passed on September 10, 2026. The corrected live cases below were verified.

## What did you change? (under 1,000 characters)

Replaced wallet-triggered sampling with contract-only self-calls after finalization. Acceptance commits each required attempt; wallets cannot choose, skip, or retry checks. All planned checks are required for a provider refund. Transport failure or an overdue/unverifiable attempt pays the beneficiary; cancellation after acceptance is removed. Pending obligations survive child rollback. On the canonical StudioNet contract, ub-2 refunded the provider after healthy checks, ub-3 paid the beneficiary for HTTP 503 failures, and ub-4 paid the beneficiary after response variance canceled a check, even when the provider called timeout settlement. All native credits were verified. Added 112 adversarial contract tests, independent validator replay, 7 receipt tests, and a real autonomous-flow integration test. Updated the UI, risk disclosures, and evidence links. These are finite network-timed checks, not continuous uptime. Contract: 0xF5E1027a28439716455F7b1778Aca17855346B87.

## Application date and identity

Use the actual resubmission date. Project name: **UptimeBond by demigodd00**.
Primary tag: **DeFi**. Tag 1 and Tag 2: leave optional sub-tags blank if none fit.
Logo: docs/assets/uptimebond/uptimebond-logo.png.

## 02 — One-liner

StudioNet health-check bonds with automatic GenLayer checks and provider-funded evidence risk.

## 03 — Description (under 1,000 characters)

UptimeBond by demigodd00 is a health-check performance-bond app on GenLayer StudioNet. Test GEN has no monetary value. A provider locks a bond against an HTTPS endpoint, expected status, proof token, required checks, and failure allowance. After validator-verified readiness, the beneficiary accepts. The contract automatically queues each check after consensus finality; participant wallets cannot choose or retry individual checks. Validators independently fetch the endpoint and compare status, token, response size, full-body SHA-256, and result without an LLM. All checks are required for a provider refund. Excess failures or unverifiable evidence pay the beneficiary. A stalled check can be settled to the beneficiary after its five-minute evidence deadline. There are no fees, admin settlement controls, or cancellation after acceptance. These are finite network-timed checks, not continuous uptime monitoring; providers bear network and evidence-availability risk.

## 04 — Demo video

Leave blank unless you have a real public or unlisted YouTube demo.

## 05 — Exact reviewer path

1. **Healthy case.** Open https://uptimebond-psi.vercel.app/bonds?bond=ub-2 without connecting a wallet.
   Confirm MET, two PASS checks, and the 0.001 test-GEN provider refund.
2. **Observed breach.** Open https://uptimebond-psi.vercel.app/bonds?bond=ub-3.
   Expand Evidence receipts; inspect HTTP 503 and the beneficiary payout.
3. **Suppressed evidence.** Open https://uptimebond-psi.vercel.app/bonds?bond=ub-4.
   Confirm UNVERIFIABLE, the committed check/deadline, no invented response hash,
   and the beneficiary payout. This case uses a clearly named public variance fixture.
4. **Trace GenLayer execution.** Open the acceptance journal below. Trace acceptance
   -> contract-sent child checks -> native credit. Manual calls from all wallet roles
   are rejected. The missing-check obligation remains after unsuccessful child execution.
5. **Verify identity.** Open https://uptimebond-psi.vercel.app/status and compare the
   full canonical address and version with the linked deployment record and Explorer.
   No signing is needed for this read-only review.

For a fresh hands-on test, use two different StudioNet wallets. Create a 0.001 GEN
bond with the default stable fixture, verify readiness as provider, then accept as
the named beneficiary. Checks run without additional wallet signatures. Missing
evidence allocates the whole test bond to the beneficiary; it is not an outage claim.

## 06 — Expected verification outcome (under 500 characters)

The app shows ub-2 MET with two automatic PASS checks and a provider refund; ub-3 BREACHED with HTTP 503 evidence and beneficiary payout; and ub-4 UNVERIFIABLE with the committed attempt preserved and beneficiary payout. Each bond is 0.001 test GEN. The acceptance journal proves child transactions and credited transfers. Status and Explorer match 0xF5E1027a28439716455F7b1778Aca17855346B87, version 0.2.0-studionet, zero fees, no admin, and zero locked test bonds.

## Contract link

https://explorer-studio.genlayer.com/address/0xF5E1027a28439716455F7b1778Aca17855346B87

## 07 — Project links

Website: https://uptimebond-psi.vercel.app
GitHub: https://github.com/Demigodd00/uptimebond

## Evidence and supporting information

- GitHub Repository: https://github.com/Demigodd00/uptimebond
- GenLayer Explorer Contract: https://explorer-studio.genlayer.com/address/0xF5E1027a28439716455F7b1778Aca17855346B87
- Other (live product): https://uptimebond-psi.vercel.app
- GitHub File (source): https://github.com/Demigodd00/uptimebond/blob/main/contracts/uptime_bond.py
- GitHub File (adversarial tests): https://github.com/Demigodd00/uptimebond/blob/main/tests/direct/test_uptime_bond.py
- GitHub File (exact-address journal): https://github.com/Demigodd00/uptimebond/blob/main/deployments/uptime_bond_acceptance.json
- GitHub File (fairness correction): https://github.com/Demigodd00/uptimebond/blob/main/docs/FAIRNESS.md
- GitHub File (release): https://github.com/Demigodd00/uptimebond/blob/main/docs/RELEASE.md

The old contract, 0x308966Eb38b57798e614E3f4B4D4011C6F84367a, is historical only.
Complete the Portal's CAPTCHA and final submission yourself. This correction does
not guarantee steward acceptance or constitute a mainnet security audit.
