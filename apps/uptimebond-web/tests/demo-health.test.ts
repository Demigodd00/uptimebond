import assert from "node:assert/strict";
import test from "node:test";
import { GET } from "../src/app/api/demo-health/route";

test("the review fixture is stable and contains the proof token", async () => {
  const first = await GET();
  const second = await GET();
  assert.equal(first.status, 200);
  assert.equal(second.status, 200);
  const firstBody = await first.text();
  const secondBody = await second.text();
  assert.equal(firstBody, secondBody);
  assert.match(firstBody, /uptimebond-demo-v1/);
  assert.match(first.headers.get("cache-control") ?? "", /public/);
});
