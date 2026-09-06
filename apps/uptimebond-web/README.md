# UptimeBond web

Production frontend for UptimeBond by demigodd00 on GenLayer StudioNet.

- Live app: https://uptimebond-psi.vercel.app
- Contract: `0x308966Eb38b57798e614E3f4B4D4011C6F84367a`
- Network: StudioNet; test GEN has no monetary value

## Local verification

```bash
pnpm install --frozen-lockfile
pnpm test
pnpm typecheck
pnpm build
pnpm audit:prod
```

Copy `.env.example` to `.env.local` only when local overrides are needed. Never place a private key in the frontend environment; wallet transactions are signed by the user's injected wallet.
