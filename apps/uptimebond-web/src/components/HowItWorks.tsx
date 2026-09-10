export default function HowItWorks() {
  return (
    <section className="how-section">
      <div className="how-heading"><p className="eyebrow">Protocol flow</p><h1>Promise. Prove. Monitor. Settle.</h1><p>A compact performance-bond workflow backed by public endpoint evidence.</p></div>
      <div className="how-grid how-grid-four">
        <article><span>01</span><h3>Lock the bond</h3><p>The provider fixes the endpoint, response terms, required check count, beneficiary, and test-GEN amount.</p></article>
        <article><span>02</span><h3>Prove readiness</h3><p>Validators confirm the endpoint serves the agreed static token before acceptance.</p></article>
        <article><span>03</span><h3>Automatic checks</h3><p>Acceptance queues the checks. Each finalized check triggers the next. Neither party chooses or retries individual checks.</p></article>
        <article><span>04</span><h3>Settle facts</h3><p>Every check is required. Within the agreed failure allowance, the bond returns to the provider; otherwise the beneficiary is paid.</p></article>
      </div>
      <div className="boundary-grid">
        <div><p className="eyebrow">GenLayer owns</p><h3>Evidence and settlement.</h3><p>Validators independently refetch the complete response and require exact agreement on the status, token, size, and SHA-256 digest.</p></div>
        <div><p className="eyebrow">Evidence risk</p><h3>Missing evidence never refunds the provider.</h3><p>Unverifiable fetches pay the beneficiary. If a queued check stalls for five minutes, any wallet can settle it to the beneficiary. No verified response is not proof of an outage.</p></div>
      </div>
      <div className="scope-note"><strong>StudioNet experiment</strong><span>Test GEN has no monetary value. These are finite, network-timed consensus checks—not fixed-interval, random, or continuous monitoring. Providers bear network and evidence-availability risk. No admin settlement.</span></div>
    </section>
  );
}
