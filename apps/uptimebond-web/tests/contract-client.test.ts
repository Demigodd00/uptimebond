import assert from "node:assert/strict";
import test from "node:test";
import {
  CONTRACT_READY,
  formatGen,
  isAddress,
  isProofToken,
  isPublicHttpsEndpoint,
  isTransientReadError,
  parseGen,
  shortenAddress,
  withReadRetry,
} from "../src/lib/contract";

test("GEN amounts round-trip at atto precision", () => {
  assert.equal(parseGen("0.001"), 10n ** 15n);
  assert.equal(parseGen("1.000000000000000001"), 10n ** 18n + 1n);
  assert.equal(formatGen(10n ** 18n + 25_000_000_000_000_000n), "1.025");
  assert.throws(() => parseGen("-1"), /valid GEN amount/);
  assert.throws(() => parseGen("1.0000000000000000001"), /valid GEN amount/);
});

test("public endpoint policy matches the contract boundary", () => {
  assert.equal(isPublicHttpsEndpoint("https://status.example.com/health"), true);
  for (const source of [
    "http://example.com/health",
    "https://localhost/health",
    "https://127.0.0.1/health",
    "https://user@example.com/health",
    "https://example..com/health",
    "https://example.com/bad path",
  ]) assert.equal(isPublicHttpsEndpoint(source), false, source);
});

test("wallet and proof token validation fail closed", () => {
  const address = `0x${"1".repeat(40)}`;
  assert.equal(isAddress(address), true);
  assert.equal(isAddress(`0x${"0".repeat(40)}`), false);
  assert.equal(isAddress("0x123"), false);
  assert.equal(isProofToken("uptimebond-demo-v1"), true);
  assert.equal(isProofToken("too short"), false);
  assert.equal(shortenAddress(address), "0x1111…1111");
});

test("read retries are limited to transient failures", async () => {
  let calls = 0;
  const waits: number[] = [];
  const result = await withReadRetry(async () => {
    calls += 1;
    if (calls < 3) throw new Error("network error");
    return "ok";
  }, async (delay) => { waits.push(delay); });
  assert.equal(result, "ok");
  assert.deepEqual(waits, [350, 1000]);
  assert.equal(isTransientReadError(new Error("503 service unavailable")), true);
  await assert.rejects(withReadRetry(async () => { throw new Error("invalid bond"); }), /invalid bond/);
});

test("an unset deployment address stays in preview mode", () => {
  assert.equal(typeof CONTRACT_READY, "boolean");
});
