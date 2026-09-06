"use client";

import { useMemo, useState } from "react";
import {
  CONTRACT_READY,
  createBond,
  formatGen,
  friendlyError,
  isAddress,
  isProofToken,
  isPublicHttpsEndpoint,
  parseGen,
  type TxProgress,
  type WalletSession,
} from "@/lib/contract";
import { transactionPending } from "@/lib/ui-state";
import TxNotice from "./TxNotice";

const configuredSite = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://uptimebond-psi.vercel.app").replace(/\/$/, "");

function localDate(minutesAhead: number): string {
  const date = new Date(Date.now() + minutesAhead * 60_000);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

export default function CreateBond({ session, onCreated }: { session: WalletSession | null; onCreated: () => void }) {
  const [serviceName, setServiceName] = useState("UptimeBond demo API");
  const [endpointUrl, setEndpointUrl] = useState(`${configuredSite}/api/demo-health`);
  const [beneficiary, setBeneficiary] = useState("");
  const [expectedStatus, setExpectedStatus] = useState("200");
  const [proofToken, setProofToken] = useState("uptimebond-demo-v1");
  const [acceptBy, setAcceptBy] = useState(() => localDate(6));
  const [startsAt, setStartsAt] = useState(() => localDate(8));
  const [intervalMinutes, setIntervalMinutes] = useState("3");
  const [slotCount, setSlotCount] = useState("3");
  const [minObservations, setMinObservations] = useState("2");
  const [maxFailures, setMaxFailures] = useState("0");
  const [bondAmount, setBondAmount] = useState("0.001");
  const [reviewing, setReviewing] = useState(false);
  const [created, setCreated] = useState(false);
  const [progress, setProgress] = useState<TxProgress | null>(null);
  const [error, setError] = useState("");
  const busy = transactionPending(progress);

  const bondAtto = useMemo(() => {
    try { return parseGen(bondAmount); } catch { return 0n; }
  }, [bondAmount]);

  const numbers = useMemo(() => ({
    expectedStatus: Number(expectedStatus),
    intervalMinutes: Number(intervalMinutes),
    slotCount: Number(slotCount),
    minObservations: Number(minObservations),
    maxFailures: Number(maxFailures),
  }), [expectedStatus, intervalMinutes, slotCount, minObservations, maxFailures]);

  function validate(): string {
    if (!serviceName.trim() || serviceName.trim().length > 80) return "Name the service in no more than 80 characters.";
    if (!isPublicHttpsEndpoint(endpointUrl)) return "Use a public HTTPS health endpoint with a valid domain.";
    if (!isAddress(beneficiary.trim())) return "Enter the beneficiary's complete wallet address.";
    if (session && session.address.toLowerCase() === beneficiary.trim().toLowerCase()) return "Provider and beneficiary must use different wallets.";
    if (!Number.isInteger(numbers.expectedStatus) || numbers.expectedStatus < 100 || numbers.expectedStatus > 599) return "Expected HTTP status must be between 100 and 599.";
    if (!isProofToken(proofToken)) return "Use an 8–96 character proof token containing letters, numbers, dots, colons, slashes, underscores, or hyphens.";
    if (bondAtto < 10n ** 15n || bondAtto > 10n * 10n ** 18n) return "Choose a test bond between 0.001 and 10 GEN.";
    const acceptAt = new Date(acceptBy).getTime();
    const startAt = new Date(startsAt).getTime();
    if (!Number.isFinite(acceptAt) || acceptAt < Date.now() + 2 * 60_000) return "Set acceptance at least two minutes from now.";
    if (!Number.isFinite(startAt) || startAt < acceptAt + 60_000) return "Start monitoring at least one minute after acceptance closes.";
    if (!Number.isInteger(numbers.intervalMinutes) || numbers.intervalMinutes < 1 || numbers.intervalMinutes > 1440) return "Choose a check interval from 1 to 1,440 minutes.";
    if (!Number.isInteger(numbers.slotCount) || numbers.slotCount < 2 || numbers.slotCount > 12) return "Choose between 2 and 12 monitoring slots.";
    if (!Number.isInteger(numbers.minObservations) || numbers.minObservations < 1 || numbers.minObservations > numbers.slotCount) return "Minimum observations must be between 1 and the number of slots.";
    if (!Number.isInteger(numbers.maxFailures) || numbers.maxFailures < 0 || numbers.maxFailures >= numbers.minObservations) return "Allowed failures must be lower than minimum observations.";
    if (numbers.intervalMinutes * 60 * numbers.slotCount > 7 * 24 * 60 * 60) return "Monitoring cannot exceed seven days.";
    return "";
  }

  function openReview() {
    const nextError = validate();
    setError(nextError);
    if (!nextError) setReviewing(true);
  }

  async function submit() {
    if (busy) return;
    if (!session) { setError("Connect the provider wallet before locking the bond."); return; }
    if (!CONTRACT_READY) { setError("Transactions are unavailable in preview mode."); return; }
    const nextError = validate();
    if (nextError) { setError(nextError); return; }
    setError("");
    try {
      await createBond(session, {
        serviceName: serviceName.trim(),
        endpointUrl: endpointUrl.trim(),
        beneficiary: beneficiary.trim() as `0x${string}`,
        expectedStatus: numbers.expectedStatus,
        proofToken: proofToken.trim(),
        acceptByUnix: Math.floor(new Date(acceptBy).getTime() / 1000),
        startsAtUnix: Math.floor(new Date(startsAt).getTime() / 1000),
        intervalSecs: numbers.intervalMinutes * 60,
        slotCount: numbers.slotCount,
        minObservations: numbers.minObservations,
        maxFailures: numbers.maxFailures,
        bondAtto,
      }, setProgress);
      setCreated(true);
      onCreated();
    } catch (reason) {
      setError(friendlyError(reason));
    }
  }

  if (created) {
    return (
      <section className="success-panel">
        <span className="success-mark">✓</span>
        <p className="eyebrow">Bond confirmed</p>
        <h1>Offer created.</h1>
        <p>Verify endpoint readiness, then share the bond with its beneficiary.</p>
        <div className="success-actions">
          <a className="button button-primary" href="/bonds">Open bonds</a>
          <button className="button button-secondary" onClick={() => { setCreated(false); setReviewing(false); setProgress(null); }}>Create another</button>
        </div>
      </section>
    );
  }

  return (
    <section className="create-layout">
      <aside className="template-panel">
        <p className="eyebrow">Safe demo</p>
        <h2>A static health proof.</h2>
        <p>The template targets this app&apos;s stable endpoint and a fixed response token.</p>
        <button className="template-card" type="button" onClick={() => {
          if (busy) return;
          setServiceName("UptimeBond demo API");
          setEndpointUrl(`${configuredSite}/api/demo-health`);
          setExpectedStatus("200");
          setProofToken("uptimebond-demo-v1");
        }} disabled={busy}>
          <span>HEALTH FIXTURE</span><strong>HTTP 200 + proof token</strong><small>{configuredSite.replace(/^https:\/\//, "")}</small>
        </button>
        <div className="mini-rule"><span>01</span><p>Provider locks the test bond.</p></div>
        <div className="mini-rule"><span>02</span><p>Beneficiary accepts verified terms.</p></div>
        <div className="mini-rule"><span>03</span><p>Validators record fixed-slot checks.</p></div>
      </aside>

      <div className="form-card">
        <div className="form-heading">
          <div><p className="eyebrow">{reviewing ? "Final review" : "New performance bond"}</p><h1>{reviewing ? "Lock these terms?" : "Define the uptime promise."}</h1></div>
          <span>{reviewing ? "02 / 02" : "01 / 02"}</span>
        </div>
        {reviewing ? (
          <div className="review-stack">
            <div className="review-service"><span>SERVICE</span><h2>{serviceName}</h2><a href={endpointUrl} target="_blank" rel="noreferrer">{endpointUrl} ↗</a></div>
            <dl className="review-grid">
              <div><dt>Bond</dt><dd>{formatGen(bondAtto)} test GEN</dd></div>
              <div><dt>Beneficiary</dt><dd className="mono">{beneficiary}</dd></div>
              <div><dt>Healthy response</dt><dd>HTTP {expectedStatus} + token</dd></div>
              <div><dt>Monitoring</dt><dd>{slotCount} slots · every {intervalMinutes}m</dd></div>
              <div><dt>Evidence threshold</dt><dd>{minObservations} observations minimum</dd></div>
              <div><dt>Failure allowance</dt><dd>{maxFailures}</dd></div>
            </dl>
            <div className="terms-note"><strong>Immutable after confirmation</strong><span>Readiness must pass before the beneficiary can accept.</span></div>
            <div className="form-actions"><button className="button button-secondary" onClick={() => setReviewing(false)} disabled={busy}>Edit terms</button><button className="button button-primary" onClick={() => void submit()} disabled={busy}>{CONTRACT_READY ? "Lock test bond" : "Preview only"}</button></div>
          </div>
        ) : (
          <div className="form-stack">
            <div className="field-row">
              <label><span>Service name</span><input maxLength={80} value={serviceName} onChange={(event) => setServiceName(event.target.value)} /></label>
              <label><span>Beneficiary wallet</span><input spellCheck={false} placeholder="0x…" value={beneficiary} onChange={(event) => setBeneficiary(event.target.value)} /></label>
            </div>
            <label><span>Public HTTPS health endpoint</span><input type="url" spellCheck={false} value={endpointUrl} onChange={(event) => setEndpointUrl(event.target.value)} /><small>Use a stable UTF-8 response no larger than 16 KB.</small></label>
            <div className="field-row field-row-narrow">
              <label><span>Expected HTTP status</span><input inputMode="numeric" value={expectedStatus} onChange={(event) => setExpectedStatus(event.target.value)} /></label>
              <label><span>Required proof token</span><input spellCheck={false} maxLength={96} value={proofToken} onChange={(event) => setProofToken(event.target.value)} /></label>
              <label><span>Test bond in GEN</span><input inputMode="decimal" value={bondAmount} onChange={(event) => setBondAmount(event.target.value)} /></label>
            </div>
            <div className="field-row">
              <label><span>Accept by</span><input type="datetime-local" value={acceptBy} onChange={(event) => setAcceptBy(event.target.value)} /></label>
              <label><span>Monitoring starts</span><input type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label>
            </div>
            <div className="field-row field-row-four">
              <label><span>Interval (minutes)</span><input inputMode="numeric" value={intervalMinutes} onChange={(event) => setIntervalMinutes(event.target.value)} /></label>
              <label><span>Slots</span><input inputMode="numeric" value={slotCount} onChange={(event) => setSlotCount(event.target.value)} /></label>
              <label><span>Minimum checks</span><input inputMode="numeric" value={minObservations} onChange={(event) => setMinObservations(event.target.value)} /></label>
              <label><span>Allowed failures</span><input inputMode="numeric" value={maxFailures} onChange={(event) => setMaxFailures(event.target.value)} /></label>
            </div>
            <button className="button button-primary button-wide" type="button" onClick={openReview}>Review bond</button>
          </div>
        )}
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <TxNotice progress={progress} />
      </div>
    </section>
  );
}
