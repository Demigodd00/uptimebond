import { randomUUID } from "node:crypto";

export const dynamic = "force-dynamic";

// Public, stateless adversarial fixture. The complete transition is committed
// in the bond's URL; no dashboard toggle, secret, or privileged endpoint exists.
export async function GET(request: Request) {
  const url = new URL(request.url);
  const scenario = url.searchParams.get("case");
  const switchAt = Number(url.searchParams.get("switch_at"));
  if (!["breach", "variance"].includes(scenario ?? "") || !Number.isSafeInteger(switchAt) || switchAt <= 0) {
    return Response.json({ error: "Use case=breach|variance and a positive Unix switch_at." }, { status: 400 });
  }
  const switched = Date.now() >= switchAt * 1000;
  const payload: Record<string, string> = { product: "UptimeBond", service: "review-fixture", proof: "uptimebond-demo-v1" };
  if (switched && scenario === "variance") payload.nonce = randomUUID();
  return Response.json(payload, {
    status: switched && scenario === "breach" ? 503 : 200,
    headers: { "Cache-Control": "no-store, max-age=0", "X-UptimeBond-Fixture": scenario ?? "" },
  });
}
