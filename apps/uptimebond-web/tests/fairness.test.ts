import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { GET as fixture } from "../src/app/api/review-health/route";

test("the fixture transition is determined by its committed URL", async () => {
  const future = Math.floor(Date.now() / 1000) + 100;
  const ready = await fixture(new Request(`https://example.com/api/review-health?case=breach&switch_at=${future}`));
  assert.equal(ready.status, 200);
  assert.match(await ready.text(), /uptimebond-demo-v1/);
  const failed = await fixture(new Request("https://example.com/api/review-health?case=breach&switch_at=1"));
  assert.equal(failed.status, 503);
  assert.match(failed.headers.get("cache-control") ?? "", /no-store/);
});

test("variance fixture actually returns different complete bodies", async () => {
  const url = "https://example.com/api/review-health?case=variance&switch_at=1";
  const first = await fixture(new Request(url));
  const second = await fixture(new Request(url));
  assert.equal(first.status, 200);
  assert.notEqual(await first.text(), await second.text());
  assert.equal((await fixture(new Request("https://example.com/api/review-health"))).status, 400);
});

test("UI cannot submit caller-selected checks or active cancellation", () => {
  const client = readFileSync("src/lib/contract.ts", "utf8");
  const board = readFileSync("src/components/BondBoard.tsx", "utf8");
  const create = readFileSync("src/components/CreateBond.tsx", "utf8");
  assert.doesNotMatch(client, /write\(session, "(record_observation|request_cancellation|withdraw_cancellation_request)"/);
  assert.doesNotMatch(create, /startsAtUnix|minObservations|intervalSecs/);
  assert.match(create, /Every check is required/);
  assert.match(create, /disabled=\{busy \|\| !riskAccepted\}/);
  assert.match(board, /disabled=\{busy \|\| !acceptTerms\}/);
  assert.match(board, /No verifiable response\. This is not proof of an outage/);
  assert.equal((client.match(/readClient\.readContract\(/g) ?? []).length,
    (client.match(/transactionHashVariant: TransactionHashVariant\.LATEST_FINAL/g) ?? []).length,
    "all displayed contract facts must come from finalized state");
});
