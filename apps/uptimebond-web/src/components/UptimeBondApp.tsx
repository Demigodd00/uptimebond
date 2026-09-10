import Link from "next/link";
import { CONTRACT_READY } from "@/lib/contract";

export default function UptimeBondApp() {
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span />Public uptime · bonded on GenLayer</p>
          <h1>Put uptime<br />on the line.</h1>
          <p className="hero-summary">Lock a test-GEN performance bond. Independent validators check the endpoint. The contract settles the result.</p>
          <div className="hero-actions">
            <Link className="button button-primary button-large" href="/bonds/new">Create a bond <span>↗</span></Link>
            <Link className="button button-secondary button-large" href="/bonds">Open monitor</Link>
          </div>
          <p className="environment-note">{CONTRACT_READY ? "Canonical StudioNet contract connected" : "Interactive preview · transactions disabled until deployment"}</p>
        </div>
        <div className="hero-monitor" aria-label="Illustrative uptime monitor">
          <div className="monitor-glow" />
          <div className="monitor-card">
            <div className="monitor-top"><span><i /> EXAMPLE CHECKS</span><small>ILLUSTRATION</small></div>
            <div className="uptime-number"><strong>11</strong><span>/ 12</span></div>
            <div className="pulse-chart" aria-hidden="true">
              <svg viewBox="0 0 520 150" preserveAspectRatio="none">
                <path className="grid-line" d="M0 30H520M0 75H520M0 120H520" />
                <path className="pulse-fill" d="M0 105 C32 104 38 92 65 94 S104 106 132 88 S171 43 195 68 S228 101 260 92 S292 38 318 58 S348 111 380 82 S420 70 449 46 S483 79 520 35 V150 H0Z" />
                <path className="pulse-line" d="M0 105 C32 104 38 92 65 94 S104 106 132 88 S171 43 195 68 S228 101 260 92 S292 38 318 58 S348 111 380 82 S420 70 449 46 S483 79 520 35" />
              </svg>
            </div>
            <div className="monitor-stats"><div><span>CHECKS</span><strong>11 / 12</strong></div><div><span>FAILURES</span><strong>0 allowed</strong></div><div><span>BOND</span><strong>0.01 test GEN</strong></div></div>
          </div>
          <div className="signal-card signal-live"><span>●</span><div><small>VALIDATOR CHECK</small><strong>HTTP 200 · token found</strong></div></div>
          <div className="signal-card signal-proof"><small>EVIDENCE</small><strong>SHA-256 locked</strong></div>
        </div>
      </section>
      <section className="trust-strip" aria-label="Protocol properties">
        <div><span>01</span><strong>Automatic validator checks</strong></div>
        <div><span>02</span><strong>Exact evidence consensus</strong></div>
        <div><span>03</span><strong>No admin settlement</strong></div>
      </section>
    </>
  );
}
