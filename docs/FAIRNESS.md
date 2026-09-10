# UptimeBond 0.2 — sampling and settlement correction

The September 10 steward review identified two valid issues in 0.1: a caller
could choose a favorable instant within a slot, and withholding or varying
evidence could produce an insufficient-evidence refund to the provider.

## Contract boundary and chosen correction

The beneficiary's acceptance now commits the complete check count. Acceptance
records the first pending attempt and emits a self-call on finalization. Only
the canonical contract itself can execute a check. Each completed check records
its evidence and queues the next self-call on finalization. Network consensus
progress determines the sequence; no participant, keeper, or application server
chooses a check time or retries a failed check. The finite sequence is bounded
to 2–12 checks, with a five-minute evidence deadline per pending attempt.

This changes the product from manually sampled clock slots to an autonomous
sequence of consensus checkpoints. It does not claim fixed wall-clock sampling,
random sampling, continuous uptime, or immunity to validator/network censorship.
The network's scheduling and finality remain explicit dependencies.

GenLayer validators independently fetch the public endpoint and compare status,
token presence, response bounds, full-body SHA-256, and the derived result. The
frontend displays contract facts and signs offer/acceptance/recovery actions;
it does not generate observations or determine settlement.

## Economic invariants

- A provider refund after acceptance requires every planned check to be resolved
  and failures to be within the beneficiary-accepted allowance.
- Transport errors and expired or unverifiable attempts never produce a provider
  refund. The beneficiary receives the bond under a disclosed evidence-risk rule;
  the record does not call an unavailable measurement proof of an outage.
- A pending attempt is committed by its parent transaction before the fetch.
  Disagreement, exceptions, dropped child transactions, and rollback cannot erase
  the parent's obligation or turn the absence of evidence into a pass.
- No public retry, caller-supplied sample, skipping, reordering, or active
  cancellation path can replace an unfavorable committed sequence.
- Cancellation, decline, and expiry refunds remain available only before
  acceptance. Terminal accounting precedes a single finalized value transfer.

## Adversarial verification required before resubmission

Test all callers (including a third wallet) trying to choose a check instant;
duplicates, reordered and late self-calls; dropped and reverted child execution;
different leader/validator bytes; transport errors and oversized/malformed bodies;
partial favorable evidence; failure-to-missing substitutions under every allowed
failure budget; attempts to cancel after acceptance; and duplicate settlement.
Verify autonomous child transactions and both provider/beneficiary payout paths
against the exact new StudioNet address, then update frontend and evidence links.

Reference: https://docs.genlayer.com/developers/intelligent-contracts/features/messages
