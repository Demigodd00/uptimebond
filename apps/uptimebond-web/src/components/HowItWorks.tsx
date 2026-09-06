export default function HowItWorks() {
  return (
    <section className="how-section">
      <div className="how-heading"><p className="eyebrow">Protocol flow</p><h1>Promise. Prove. Monitor. Settle.</h1><p>A compact performance-bond workflow backed by public endpoint evidence.</p></div>
      <div className="how-grid how-grid-four">
        <article><span>01</span><h3>Lock the bond</h3><p>The provider fixes the endpoint, response terms, schedule, beneficiary, and test-GEN amount.</p></article>
        <article><span>02</span><h3>Prove readiness</h3><p>Validators confirm the endpoint serves the agreed static token before acceptance.</p></article>
        <article><span>03</span><h3>Record slots</h3><p>Anyone may trigger one independent validator observation in each fixed slot.</p></article>
        <article><span>04</span><h3>Settle facts</h3><p>The contract returns the bond or pays the beneficiary from the recorded checks.</p></article>
      </div>
      <div className="boundary-grid">
        <div><p className="eyebrow">GenLayer owns</p><h3>Evidence and settlement.</h3><p>Validators independently refetch the complete response and require exact agreement on the status, token, size, and SHA-256 digest.</p></div>
        <div><p className="eyebrow">Deliberate limit</p><h3>No invented uptime.</h3><p>Missing observations become inconclusive. Transport failures can be retried. Only received, agreed responses count.</p></div>
      </div>
      <div className="scope-note"><strong>StudioNet experiment</strong><span>Test GEN has no monetary value. UptimeBond measures public HTTP response compliance—not latency, global availability, insurance, or a legal SLA.</span></div>
    </section>
  );
}
