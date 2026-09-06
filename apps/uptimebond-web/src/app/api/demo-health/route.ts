export const dynamic = "force-static";

export async function GET() {
  return Response.json(
    {
      product: "UptimeBond",
      service: "demo-health",
      status: "up",
      proof: "uptimebond-demo-v1",
    },
    {
      status: 200,
      headers: { "Cache-Control": "public, max-age=300, s-maxage=300, stale-while-revalidate=60" },
    },
  );
}
