import assert from "node:assert/strict";
import test from "node:test";
import { bondShareUrl, formatCountdown, formatPercent, oneTransactionAtATime, roleFor, transactionPending, watchWalletSession } from "../src/lib/ui-state";

test("share links target a specific bond", () => {
  assert.equal(bondShareUrl("https://uptimebond.example", "ub-7"), "https://uptimebond.example/bonds?bond=ub-7");
});

test("time, percentage, and role presentation are deterministic", () => {
  assert.equal(formatCountdown("1061", 1000), "1m 1s");
  assert.equal(formatCountdown("1000", 1000), "Now");
  assert.equal(formatPercent("10000"), "100%");
  assert.equal(formatPercent("9950"), "99.50%");
  assert.equal(roleFor("0xAa", "0xaa", "0xbb"), "provider");
  assert.equal(roleFor("0xBb", "0xaa", "0xbb"), "beneficiary");
  assert.equal(roleFor(undefined, "0xaa", "0xbb"), "observer");
});

test("only pending transaction states lock controls", () => {
  assert.equal(transactionPending(null), false);
  assert.equal(transactionPending({ state: "submitted", label: "sent" }), true);
  assert.equal(transactionPending({ state: "confirmed", label: "done" }), false);
});

test("duplicate writes from one wallet are blocked", async () => {
  let release!: () => void;
  const pending = oneTransactionAtATime("0xabc", () => new Promise<void>((resolve) => { release = resolve; }));
  await assert.rejects(oneTransactionAtATime("0xABC", async () => undefined), /already in progress/);
  release();
  await pending;
  await assert.doesNotReject(oneTransactionAtATime("0xabc", async () => undefined));
});

test("wallet listeners reset changed sessions and are removed", () => {
  const listeners = new Map<string, (...args: unknown[]) => void>();
  let resets = 0;
  const provider = {
    request: async () => null,
    on: (event: string, listener: (...args: unknown[]) => void) => listeners.set(event, listener),
    removeListener: (event: string) => listeners.delete(event),
  };
  const stop = watchWalletSession(provider, "0xabc", () => { resets += 1; });
  listeners.get("accountsChanged")?.(["0xabc"]);
  assert.equal(resets, 0);
  listeners.get("accountsChanged")?.(["0xdef"]);
  assert.equal(resets, 1);
  stop();
  assert.equal(listeners.size, 0);
});
