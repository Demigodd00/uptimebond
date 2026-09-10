# UptimeBond security policy

## Supported release

Version 0.2.0-studionet:
`0xF5E1027a28439716455F7b1778Aca17855346B87`.
Source SHA-256:
`415f9ee2d28da8a99e97b99d5fcde19680a5739a7cb0f41071c5a368e7f7b40f`.

This is a valueless StudioNet demonstration, not a mainnet security guarantee,
insurance product, legal SLA, or continuous monitoring service.

## Report an issue

Contact the repository owner privately with the contract address, transaction
or bond ID, reproduction steps, and expected/observed behavior. Never publish
credentials, private keys, or personal endpoint content.

## Security boundaries

- Only public, non-sensitive, stable UTF-8 HTTPS responses up to 16,000 bytes.
- Full response equality is strict. Dynamic bodies may prevent consensus.
- Parent state commits each pending attempt before a child fetch. Unsuccessful
  child execution cannot erase that obligation. No external check or retry path.
- Refunds after acceptance require all checks and the agreed failure allowance.
- Failed/unverifiable evidence cannot increase provider payout: transport failure
  or an overdue required check pays the beneficiary, including infrastructure faults.
- Five minutes is a deterministic contract-time deadline, not a promise that
  network consensus or a native transfer will finalize within five minutes.
- Timeout settlement needs a transaction. Any wallet can send it. No background
  keeper or off-chain alarm service is claimed.
- No accepted bond cancellation, provider withdrawal, admin override, or fee.
- Finality alone is not execution success. Verify child execution and payout credit.
- The browser never reports uptime or determines a payout.
- Endpoint operators may distinguish validator traffic; sampled evidence cannot
  prove global availability, continuous uptime, content authorship, or legal ownership.

The web release upgrades Next.js to 16.3.3 for
[GHSA-p293-qw3h-jr36](https://github.com/advisories/GHSA-p293-qw3h-jr36) and
[GHSA-2xp9-vwfh-vxw4](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4).
