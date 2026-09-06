import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const files = [
  "src/components/AppShell.tsx",
  "src/components/UptimeBondApp.tsx",
  "src/components/HowItWorks.tsx",
  "src/components/StatusDashboard.tsx",
].map((path) => readFileSync(join(root, path), "utf8")).join("\n");

test("the product consistently discloses StudioNet test value", () => {
  assert.match(files, /Test GEN has no monetary value/);
  assert.match(files, /StudioNet/);
});

test("the UI states the actual GenLayer and owner boundaries", () => {
  assert.match(files, /No admin settlement/);
  assert.match(files, /Validators independently refetch/);
  assert.doesNotMatch(files, /AI[- ]powered uptime/i);
  assert.doesNotMatch(files, /guaranteed global uptime/i);
});
