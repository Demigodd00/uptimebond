# UptimeBond architecture

## Product boundary

UptimeBond is a StudioNet performance-bond protocol for public HTTP health endpoints. A service provider locks valueless test GEN for a named beneficiary. GenLayer validators independently fetch the immutable endpoint during fixed monitoring slots, require exact agreement on a normalized probe result, and the Intelligent Contract returns or awards the bond when monitoring ends.

The frontend owns wallet connection, forms, non-authoritative previews, transaction progress, and convenient indexing. It never decides whether a service passed.

The Intelligent Contract owns the offer terms, readiness proof, fixed monitoring schedule, observation records, strict validator comparison, cancellation rules, locked-value accounting, and final payout.

The monitored service owns the raw public health response. UptimeBond supports deliberately static UTF-8 health responses: an exact HTTP status and required proof token are checked, while the response bytes are fingerprinted for provenance. Network-level fetch failures do not become service failures; the transaction can be retried, and an insufficient-evidence terminal path prevents permanent lockup.

## Consequential path

1. Provider creates a payable offer naming a beneficiary and locks test GEN.
2. Provider configures the public HTTPS health endpoint with the agreed token.
3. Provider asks validators to verify readiness. Exact consensus on status, token presence, response size, and SHA-256 fingerprint moves the offer to `READY`.
4. Beneficiary accepts before the immutable acceptance deadline, moving it to `ACTIVE`.
5. During each fixed slot, any account may request one observation. Validators independently refetch the endpoint and strict consensus stores one append-only record for that slot.
6. After monitoring ends, anyone may finalize:
   - failures above the agreed allowance: `BREACHED`, bond paid to beneficiary;
   - enough observations and failures within allowance: `MET`, bond returned to provider;
   - too few observations: `INCONCLUSIVE`, bond returned to provider.
7. Every value-moving terminal state is applied before its transfer is emitted, so the same bond cannot pay twice.

## State machine

```text
OFFERED -> READY -> ACTIVE -> MET
    |        |         |----> BREACHED
    |        |         |----> INCONCLUSIVE
    |        |         `----> CANCELLED (mutual)
    |        |----> DECLINED
    |        `----> EXPIRED
    `-------------> CANCELLED (provider, before acceptance)
```

## Consensus rule

UptimeBond does not use an LLM. The probe result is structured and canonical, so a custom validator independently repeats the fetch and compares every decision field exactly. Validators must agree on:

- HTTP status;
- whether it equals the expected status;
- whether the required proof token exists in the UTF-8 body;
- response-size validity;
- SHA-256 digest of the complete response bytes; and
- the derived `PASS` or failure code.

The digest requirement intentionally means dynamic health pages are unsupported. This makes the observation reproducible and the evidence receipt reviewable.

## Fairness and recovery

- The provider cannot withdraw after beneficiary acceptance.
- The beneficiary cannot create an outage result; validators fetch the endpoint themselves.
- Neither party chooses the monitoring slot; it is derived from contract time.
- Each slot can be recorded only once.
- Received non-matching HTTP responses count as failures. A validator transport/runtime failure does not write an observation.
- Missing observations are not silently called uptime. They produce an explicit `INCONCLUSIVE` result and return the performance bond to the provider.
- Active cancellation requires matching consent from both participants.
- Offers can always be cancelled or expired before acceptance, and active bonds can always be finalized after the monitoring end.

## StudioNet scope

This release uses valueless StudioNet test GEN. It measures only public HTTPS application-level availability and a static response token. It does not claim global uptime, latency, legal SLA enforcement, private-network reachability, or production insurance coverage.
