"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CONTRACT_READY,
  acceptBond,
  cancelOffer,
  declineBond,
  expireOffer,
  finalizeBond,
  formatGen,
  friendlyError,
  getBond,
  getObservations,
  listBonds,
  recordObservation,
  requestCancellation,
  shortenAddress,
  verifyReadiness,
  withdrawCancellation,
  type BondSummary,
  type BondView,
  type ObservationRecord,
  type TxProgress,
  type WalletSession,
} from "@/lib/contract";
import { bondShareUrl, formatCountdown, formatPercent, roleFor, transactionPending } from "@/lib/ui-state";
import TxNotice from "./TxNotice";

const previewBond: BondView = {
  id: "ub-preview",
  service_name: "Atlas API Gateway",
  status: "ACTIVE",
  provider: "0x8a7F943b8C9B22D9aA8D3c05F44A2221090Be710",
  beneficiary: "0x5C3e2aB8D81E16C90be78020b2A53C71B59a4F31",
  bond_atto: "10000000000000000",
  endpoint_url: "https://uptimebond-psi.vercel.app/api/demo-health",
  expected_status: "200",
  proof_token: "uptimebond-demo-v1",
  accept_by_unix: "1799000000",
  starts_at_unix: "1800000000",
  ends_at_unix: "1800001080",
  interval_secs: "360",
  slot_count: "3",
  min_observations: "2",
  max_failures: "0",
  created_at_unix: "1798999000",
  created_at_iso: "2027-01-03T09:16:40+00:00",
  accepted_at_unix: "1798999800",
  accepted_at_iso: "2027-01-03T09:30:00+00:00",
  readiness: {
    exists: true,
    http_status: "200",
    body_digest: "3ca2c1474c873ad828248ccdffbc09b9c78f4a46e5561db34c98277a3f47d125",
    body_bytes: "75",
    checked_at_unix: "1798999600",
    checked_at_iso: "2027-01-03T09:26:40+00:00",
    provenance: "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH",
  },
  observed_count: "2",
  passed_count: "2",
  failed_count: "0",
  uptime_bps: "10000",
  current_slot: "2",
  current_slot_recorded: false,
  can_observe: true,
  can_finalize: false,
  can_expire: false,
  cancellation_requested: false,
  cancellation_requested_by: "",
  result: "",
  settled_at_unix: "0",
  settled_at_iso: "",
  payout_recipient: "",
  payout_atto: "0",
};

const previewObservations: ObservationRecord[] = [0, 1].map((slot) => ({
  slot_index: String(slot),
  result: "PASS",
  http_status: "200",
  status_matched: true,
  token_present: true,
  body_within_limit: true,
  body_digest: "3ca2c1474c873ad828248ccdffbc09b9c78f4a46e5561db34c98277a3f47d125",
  body_bytes: "75",
  observed_at_unix: String(1800000000 + slot * 360),
  observed_at_iso: new Date((1800000000 + slot * 360) * 1000).toISOString(),
  provenance: "GENLAYER_VALIDATORS_INDEPENDENT_STRICT_FETCH",
}));

const terminalStatuses = new Set(["MET", "BREACHED", "INCONCLUSIVE", "CANCELLED", "DECLINED", "EXPIRED"]);

function displayStatus(status: string): string {
  return status.toLowerCase().replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());
}

function displayResult(result: string): string {
  const labels: Record<string, string> = {
    SLA_MET: "terms met",
    FAILURE_ALLOWANCE_EXCEEDED: "terms breached",
    INSUFFICIENT_OBSERVATIONS: "inconclusive",
    BENEFICIARY_DECLINED: "declined",
    PROVIDER_CANCELLED: "cancelled",
    MUTUAL_CANCELLATION: "cancelled",
    ACCEPTANCE_EXPIRED: "expired",
  };
  return labels[result] ?? result.replace(/_/g, " ").toLowerCase();
}

function statusTone(status: string): string {
  if (status === "MET" || status === "READY") return "positive";
  if (status === "BREACHED") return "negative";
  if (terminalStatuses.has(status)) return "muted";
  return "live";
}

function localTime(unix: string): string {
  const value = Number(unix);
  return value > 0 ? new Date(value * 1000).toLocaleString() : "—";
}

export default function BondBoard({ session }: { session: WalletSession | null }) {
  const [items, setItems] = useState<BondSummary[]>([]);
  const [selected, setSelected] = useState<BondView | null>(null);
  const [observations, setObservations] = useState<ObservationRecord[]>([]);
  const [filter, setFilter] = useState<"ALL" | "OPEN" | "ACTIVE" | "FINAL">("ALL");
  const [lookupId, setLookupId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<TxProgress | null>(null);
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));
  const requestVersion = useRef(0);
  const busy = transactionPending(progress);

  const openBond = useCallback(async (bondId: string) => {
    if (!CONTRACT_READY) {
      setSelected(previewBond);
      setObservations(previewObservations);
      return;
    }
    const version = ++requestVersion.current;
    setLoading(true);
    setError("");
    try {
      const [bond, records] = await Promise.all([getBond(bondId), getObservations(bondId)]);
      if (version !== requestVersion.current) return;
      setSelected(bond);
      setObservations(records);
    } catch (reason) {
      if (version === requestVersion.current) setError(friendlyError(reason));
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    if (!CONTRACT_READY) {
      setItems([previewBond]);
      setSelected(previewBond);
      setObservations(previewObservations);
      setLoading(false);
      return;
    }
    try {
      const nextItems = await listBonds();
      setItems(nextItems);
      const requested = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("bond")?.trim() : "";
      const nextId = requested || selected?.id || nextItems[0]?.id;
      if (nextId) await openBond(nextId);
      else setSelected(null);
    } catch (reason) {
      setError(friendlyError(reason));
      setLoading(false);
    }
  }, [openBond, selected?.id]);

  useEffect(() => { void load(); }, []); // initial contract snapshot
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const filtered = useMemo(() => items.filter((item) => {
    if (filter === "ALL") return true;
    if (filter === "OPEN") return item.status === "OFFERED" || item.status === "READY";
    if (filter === "ACTIVE") return item.status === "ACTIVE";
    return terminalStatuses.has(item.status);
  }), [items, filter]);

  const role = selected ? roleFor(session?.address, selected.provider, selected.beneficiary) : "observer";
  const observationBySlot = useMemo(() => new Map(observations.map((item) => [Number(item.slot_index), item])), [observations]);

  async function execute(action: (active: WalletSession, update: (next: TxProgress) => void) => Promise<string>) {
    if (!selected) return;
    if (!session) { setError("Connect a wallet to submit this action."); return; }
    if (!CONTRACT_READY) { setError("Transactions are disabled in preview mode."); return; }
    if (busy) return;
    setError("");
    try {
      await action(session, setProgress);
      const [bond, records, nextItems] = await Promise.all([getBond(selected.id), getObservations(selected.id), listBonds()]);
      setSelected(bond);
      setObservations(records);
      setItems(nextItems);
    } catch (reason) {
      setError(friendlyError(reason));
    }
  }

  function lookup() {
    const value = lookupId.trim();
    if (!/^ub-\d+$/.test(value)) { setError("Enter a bond ID such as ub-1."); return; }
    void openBond(value);
  }

  async function share() {
    if (!selected) return;
    const url = bondShareUrl(window.location.origin, selected.id);
    try {
      await navigator.clipboard.writeText(url);
      setProgress({ state: "confirmed", label: "Bond link copied" });
    } catch {
      setError(`Copy this link: ${url}`);
    }
  }

  return (
    <section className="bond-workspace">
      <aside className="bond-sidebar">
        <div className="sidebar-heading"><div><p className="eyebrow">Monitor</p><h1>Performance bonds</h1></div><button className="icon-button" onClick={() => void load()} aria-label="Refresh bonds">↻</button></div>
        <div className="filter-row" role="group" aria-label="Filter bonds">
          {(["ALL", "OPEN", "ACTIVE", "FINAL"] as const).map((value) => <button className={filter === value ? "active" : ""} key={value} onClick={() => setFilter(value)}>{value}</button>)}
        </div>
        <div className="bond-list">
          {filtered.map((item) => (
            <button className={selected?.id === item.id ? "bond-list-item selected" : "bond-list-item"} key={item.id} onClick={() => void openBond(item.id)}>
              <div><span className={`status-dot ${statusTone(item.status)}`} /><strong>{item.service_name}</strong><small>{item.id} · {displayStatus(item.status)}</small></div>
              <span>{formatGen(item.bond_atto)}<small>GEN</small></span>
            </button>
          ))}
          {!loading && filtered.length === 0 ? <p className="empty-list">No bonds in this view.</p> : null}
        </div>
        <div className="bond-lookup"><label htmlFor="bond-id">Open by ID</label><div><input id="bond-id" placeholder="ub-…" value={lookupId} onChange={(event) => setLookupId(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") lookup(); }} /><button onClick={lookup}>Open</button></div></div>
      </aside>

      <div className="bond-detail">
        {loading && !selected ? <div className="loading-panel"><span /><p>Reading StudioNet…</p></div> : null}
        {!loading && !selected ? <div className="empty-panel"><p className="eyebrow">No bonds yet</p><h2>Create the first uptime promise.</h2><a className="button button-primary" href="/bonds/new">Create bond</a></div> : null}
        {selected ? (
          <>
            <header className="detail-header">
              <div><div className="detail-kicker"><span className={`status-pill ${statusTone(selected.status)}`}>{displayStatus(selected.status)}</span><span>{selected.id}</span></div><h2>{selected.service_name}</h2><a href={selected.endpoint_url} target="_blank" rel="noreferrer">{selected.endpoint_url} ↗</a></div>
              <div className="detail-actions"><button className="icon-button" onClick={() => void share()} aria-label="Copy bond link">⌁</button><button className="icon-button" onClick={() => void openBond(selected.id)} aria-label="Refresh bond">↻</button></div>
            </header>

            <div className="score-grid">
              <div className="score-main"><span>SAMPLED RESULT</span><strong>{Number(selected.observed_count) ? formatPercent(selected.uptime_bps) : "—"}</strong><small>{selected.passed_count} pass · {selected.failed_count} fail</small></div>
              <div><span>TEST BOND</span><strong>{formatGen(selected.bond_atto)} GEN</strong><small>{terminalStatuses.has(selected.status) ? displayResult(selected.result) : "locked in contract"}</small></div>
              <div><span>{selected.status === "ACTIVE" ? "MONITOR ENDS" : "CHECKS"}</span><strong>{selected.status === "ACTIVE" ? formatCountdown(selected.ends_at_unix, now) : `${selected.observed_count} / ${selected.slot_count}`}</strong><small>{localTime(selected.ends_at_unix)}</small></div>
            </div>

            <div className="parties-row">
              <div><span>PROVIDER</span><strong>{shortenAddress(selected.provider)}</strong>{role === "provider" ? <small>You</small> : null}</div>
              <span className="parties-arrow">→</span>
              <div><span>BENEFICIARY</span><strong>{shortenAddress(selected.beneficiary)}</strong>{role === "beneficiary" ? <small>You</small> : null}</div>
              <div className="proof-chip"><span className={selected.readiness.exists ? "proof-ready" : ""} />{selected.readiness.exists ? "Readiness proven" : "Awaiting readiness"}</div>
            </div>

            <section className="slots-section">
              <div className="section-heading"><div><p className="eyebrow">Validator observations</p><h3>Fixed monitoring slots</h3></div><span>{selected.min_observations} required · {selected.max_failures} failures allowed</span></div>
              <div className="slot-grid">
                {Array.from({ length: Number(selected.slot_count) }, (_, slot) => {
                  const record = observationBySlot.get(slot);
                  const active = selected.status === "ACTIVE" && Number(selected.current_slot) === slot;
                  return <div className={`slot ${record?.result === "PASS" ? "passed" : record ? "failed" : active ? "current" : ""}`} key={slot}><span>{String(slot + 1).padStart(2, "0")}</span><i /> <strong>{record ? (record.result === "PASS" ? "PASS" : "FAIL") : active ? "DUE" : "—"}</strong>{record ? <small>HTTP {record.http_status}</small> : <small>{localTime(String(Number(selected.starts_at_unix) + slot * Number(selected.interval_secs)))}</small>}</div>;
                })}
              </div>
            </section>

            <section className="terms-section">
              <div className="terms-grid">
                <div><span>EXPECTED RESPONSE</span><strong>HTTP {selected.expected_status}</strong></div>
                <div><span>PROOF TOKEN</span><strong className="mono">{selected.proof_token}</strong></div>
                <div><span>INTERVAL</span><strong>{Math.round(Number(selected.interval_secs) / 60)} minutes</strong></div>
                <div><span>MINIMUM EVIDENCE</span><strong>{selected.min_observations} of {selected.slot_count}</strong></div>
              </div>
            </section>

            {observations.length > 0 ? (
              <details className="evidence-panel">
                <summary>Evidence receipts <span>{observations.length}</span></summary>
                <div className="evidence-list">{observations.map((record) => <article key={record.slot_index}><div><span className={`status-dot ${record.result === "PASS" ? "positive" : "negative"}`} /><strong>Slot {Number(record.slot_index) + 1} · {record.result.replace(/_/g, " ")}</strong><small>{localTime(record.observed_at_unix)}</small></div><dl><div><dt>HTTP</dt><dd>{record.http_status}</dd></div><div><dt>Token</dt><dd>{record.token_present ? "Found" : "Missing"}</dd></div><div><dt>Bytes</dt><dd>{record.body_bytes}</dd></div></dl><code>{record.body_digest}</code></article>)}</div>
              </details>
            ) : null}

            <section className="next-action">
              <div><p className="eyebrow">Next action</p><h3>{terminalStatuses.has(selected.status) ? "Settlement complete" : selected.status === "OFFERED" ? "Prove endpoint readiness" : selected.status === "READY" ? "Beneficiary review" : selected.can_finalize ? "Monitoring complete" : selected.can_observe ? "Current slot is open" : "Waiting for the next slot"}</h3><p>Acting as {role}{session ? ` · ${shortenAddress(session.address)}` : " · wallet not connected"}</p></div>
              <div className="action-buttons">
                {selected.status === "OFFERED" && role === "provider" ? <button className="button button-primary" disabled={busy} onClick={() => void execute((active, update) => verifyReadiness(active, selected.id, update))}>Verify readiness</button> : null}
                {(selected.status === "OFFERED" || selected.status === "READY") && role === "provider" ? <button className="button button-danger" disabled={busy} onClick={() => void execute((active, update) => cancelOffer(active, selected.id, update))}>Cancel offer</button> : null}
                {selected.status === "READY" && role === "beneficiary" ? <button className="button button-primary" disabled={busy} onClick={() => void execute((active, update) => acceptBond(active, selected.id, update))}>Accept bond</button> : null}
                {(selected.status === "OFFERED" || selected.status === "READY") && role === "beneficiary" ? <button className="button button-danger" disabled={busy} onClick={() => void execute((active, update) => declineBond(active, selected.id, update))}>Decline</button> : null}
                {selected.can_expire ? <button className="button button-secondary" disabled={busy} onClick={() => void execute((active, update) => expireOffer(active, selected.id, update))}>Expire offer</button> : null}
                {selected.can_observe ? <button className="button button-primary" disabled={busy} onClick={() => void execute((active, update) => recordObservation(active, selected.id, update))}>Run validator check</button> : null}
                {selected.can_finalize ? <button className="button button-primary" disabled={busy} onClick={() => void execute((active, update) => finalizeBond(active, selected.id, update))}>Finalize bond</button> : null}
                {selected.status === "ACTIVE" && role !== "observer" && !selected.cancellation_requested ? <button className="button button-secondary" disabled={busy} onClick={() => void execute((active, update) => requestCancellation(active, selected.id, update))}>Request cancellation</button> : null}
                {selected.status === "ACTIVE" && selected.cancellation_requested && role !== "observer" && session?.address.toLowerCase() === selected.cancellation_requested_by.toLowerCase() ? <button className="button button-secondary" disabled={busy} onClick={() => void execute((active, update) => withdrawCancellation(active, selected.id, update))}>Withdraw request</button> : null}
                {selected.status === "ACTIVE" && selected.cancellation_requested && role !== "observer" && session?.address.toLowerCase() !== selected.cancellation_requested_by.toLowerCase() ? <button className="button button-danger" disabled={busy} onClick={() => void execute((active, update) => requestCancellation(active, selected.id, update))}>Confirm cancellation</button> : null}
              </div>
            </section>
            {error ? <p className="form-error" role="alert">{error}</p> : null}
            <TxNotice progress={progress} />
            {!CONTRACT_READY ? <p className="preview-note">Preview record · deploy the StudioNet contract to enable transactions.</p> : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
