import { CONTRACT_ADDRESS, CONTRACT_READY, NETWORK_NAME } from "@/lib/contract";

export async function GET() {
  return Response.json({
    product: "UptimeBond",
    release: "0.1.0",
    network: NETWORK_NAME,
    contractAddress: CONTRACT_READY ? CONTRACT_ADDRESS : null,
    contractConfigured: CONTRACT_READY,
    studioNetConfigured: NETWORK_NAME === "StudioNet",
    readyForStudioNetTesting: CONTRACT_READY && NETWORK_NAME === "StudioNet",
    adminSettlement: false,
    feeBps: 0,
  });
}
