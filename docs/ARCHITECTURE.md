# UptimeBond 0.2 architecture

The Intelligent Contract owns immutable offer terms, readiness, queued attempts,
independent validator comparison, eligibility, evidence risk, and payout.
The frontend owns wallet connection, forms, read-only polling, and transaction
progress. It cannot fabricate a result, schedule a check, or choose a payout.

## Execution sequence

1. Provider creates a payable offer; status OFFERED.
2. Provider readiness fetch passes strict independent validation; status READY.
3. Beneficiary accepts before the deadline; status ACTIVE. Parent state records
   check 0 PENDING with a five-minute evidence deadline and emits a self-call.
4. After parent finalization, the contract executes that child. The only permitted
   immediate sender is the contract address, not the transaction origin.
5. Each finalized child stores its response and commits/queues the next child.
   All 2–12 checks are required; no public retry or clock-slot selection exists.
6. Complete evidence within allowance returns the bond (MET). Excess observed
   failures pay the beneficiary (BREACHED). Canonical fetch unavailability pays
   the beneficiary (UNVERIFIABLE). A missing/rolled-back/disputed child leaves
   its parent's PENDING record intact. After its deadline any wallet can finalize
   UNVERIFIABLE, paying the beneficiary.
7. Accounting and terminal state precede a single native transfer emitted on
   finalization. Duplicate writes cannot cause duplicate payouts.

## State transitions

OFFERED -> READY -> ACTIVE -> MET / BREACHED / UNVERIFIABLE.
OFFERED or READY -> CANCELLED / DECLINED / EXPIRED (provider refund).
There is no active cancellation.

## Evidence and consensus

Each received response is independently fetched by leader and validators.
Exact agreement covers HTTP status, status match, token presence, size validity,
full-body SHA-256 and byte count, and derived result. No LLM is used.

A PENDING or UNVERIFIABLE_TIMEOUT record contains committed scheduling and deadline
facts, not an invented response hash or HTTP status. Transport exceptions produce
a canonical UNVERIFIABLE_FETCH record. Missing evidence is an agreed allocation
of evidence risk, not proof of downtime.

## Timing and trust

This is a finite series of finality-driven checkpoints. It is not fixed wall-clock
sampling, continuous uptime, random sampling, or censorship-resistant scheduling.
Acceptance starts the sequence; participant wallets cannot choose later probes.
Network consensus scheduling determines when the actual independent fetches occur.
Providers accept infrastructure and evidence-availability risk.

The public /api/demo-health fixture is stable. /api/review-health is a stateless,
clearly named adversarial fixture: its URL commits a transition timestamp and
either an HTTP 503 case or varying body bytes. Neither fixture is an oracle input
controlled by a privileged contract administrator.
