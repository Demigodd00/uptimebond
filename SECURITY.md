# UptimeBond security policy

## Supported release

The supported StudioNet release is contract `0x308966Eb38b57798e614E3f4B4D4011C6F84367a` with source SHA-256 `d79ea8561dc7da6a1f2a28906a59b01d7b5022aa3bccb321454884c658753481` and the production app at https://uptimebond-psi.vercel.app.

This is a valueless StudioNet demonstration and has not been represented as a mainnet audit, insurance product, legal SLA, or continuous monitoring service.

## Report a vulnerability

Report security issues privately to the repository owner before public disclosure. Include the affected contract address and version, transaction or bond ID, reproduction steps, expected invariant, and observed result. Do not place credentials, private keys, private endpoint content, or personal data in an issue.

## Security boundaries

- Use only public, non-sensitive, static UTF-8 HTTPS health endpoints no larger than 16 KB.
- Never place a signer key, seed phrase, wallet export, or API credential in the repository or frontend environment.
- Never configure the frontend with an address that differs from the recorded canonical deployment.
- A finalized transaction is not treated as successful until its execution result is checked.
- Missing observations become inconclusive; transport errors never fabricate a failed observation.
- The deployer has no admin settlement role, fee withdrawal, or mechanism to redirect locked value.
- A keeper or participant must trigger each monitoring slot; the contract does not schedule its own transactions.
