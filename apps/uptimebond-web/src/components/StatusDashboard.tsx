"use client";

import { useEffect, useState } from "react";
import { CONTRACT_ADDRESS, CONTRACT_EXPLORER_URL, CONTRACT_READY, NETWORK_NAME, formatGen, friendlyError, getStats, shortenAddress, type ProtocolStats } from "@/lib/contract";

const previewStats: ProtocolStats = {
  total_created: "0",
  total_finalized: "0",
  total_met: "0",
  total_breached: "0",
  total_inconclusive: "0",
  total_locked_atto: "0",
  total_returned_to_providers_atto: "0",
  total_paid_to_beneficiaries_atto: "0",
  fee_bps: "0",
  admin_controls: false,
  experimental: true,
  max_page_size: "25",
  max_response_bytes: "16000",
  probe_policy: "STRICT_INDEPENDENT_STATUS_TOKEN_SIZE_AND_SHA256",
  version: "0.1.0-studionet",
};

export default function StatusDashboard() {
  const [stats, setStats] = useState<ProtocolStats>(previewStats);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(CONTRACT_READY);

  useEffect(() => {
    if (!CONTRACT_READY) return;
    getStats().then(setStats).catch((reason) => setError(friendlyError(reason))).finally(() => setLoading(false));
  }, []);

  return (
    <section className="status-page">
      <header className="status-hero"><div><p className="eyebrow">Release status</p><h1>{CONTRACT_READY ? "StudioNet connected." : "Ready for deployment."}</h1><p>{loading ? "Reading the canonical contract…" : `UptimeBond ${stats.version}`}</p></div><a className="contract-card" href={CONTRACT_EXPLORER_URL} target="_blank" rel="noreferrer"><span className={CONTRACT_READY ? "ready" : ""} /><div><small>CANONICAL CONTRACT</small><strong>{CONTRACT_READY ? shortenAddress(CONTRACT_ADDRESS) : "Not configured"}</strong></div><b>↗</b></a></header>
      <div className="health-grid">
        <div className={CONTRACT_READY ? "ready" : ""}><span><strong>Frontend</strong>{CONTRACT_READY ? "Contract configured" : "Preview mode"}</span></div>
        <div className={NETWORK_NAME === "StudioNet" ? "ready" : ""}><span><strong>Network</strong>{NETWORK_NAME}</span></div>
        <div className={!stats.admin_controls && stats.fee_bps === "0" ? "ready" : ""}><span><strong>Control</strong>No admin · zero fee</span></div>
      </div>
      <div className="status-metrics"><div><span>BONDS</span><strong>{stats.total_created}</strong></div><div><span>FINALIZED</span><strong>{stats.total_finalized}</strong></div><div><span>MET</span><strong>{stats.total_met}</strong></div><div><span>BREACHED</span><strong>{stats.total_breached}</strong></div><div><span>LOCKED</span><strong>{formatGen(stats.total_locked_atto)} GEN</strong></div></div>
      <div className="policy-card"><div><p className="eyebrow">Consensus policy</p><h2>Strict independent endpoint fetches</h2></div><dl><div><dt>Response cap</dt><dd>{Number(stats.max_response_bytes).toLocaleString()} bytes</dd></div><div><dt>Fee</dt><dd>{stats.fee_bps} bps</dd></div><div><dt>Admin settlement</dt><dd>{stats.admin_controls ? "Enabled" : "None"}</dd></div></dl><code>{stats.probe_policy}</code></div>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <div className="status-notice"><strong>Test environment</strong><p>StudioNet GEN is valueless. Use public, non-sensitive health endpoints only.</p></div>
    </section>
  );
}
