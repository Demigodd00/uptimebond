import { chains, createClient } from "genlayer-js";
import { TransactionStatus } from "genlayer-js/types";
import { assertSuccessfulExecution } from "./receipt";
import { oneTransactionAtATime } from "./ui-state";
import { connectStudioWallet, type EthereumProvider, type WalletOption } from "./wallet";

export type { EthereumProvider } from "./wallet";
export type Address = `0x${string}`;

export interface WalletSession {
  address: Address;
  client: ReturnType<typeof createClient>;
  provider: EthereumProvider;
  walletName: string;
}

export interface BondSummary {
  id: string;
  service_name: string;
  status: string;
  provider: string;
  beneficiary: string;
  bond_atto: string;
  observed_count: string;
  passed_count: string;
  failed_count: string;
}

export interface ReadinessRecord {
  exists: boolean;
  http_status: string;
  body_digest: string;
  body_bytes: string;
  checked_at_unix: string;
  checked_at_iso: string;
  provenance: string;
}

export interface ObservationRecord {
  slot_index: string;
  result: string;
  http_status: string;
  status_matched: boolean;
  token_present: boolean;
  body_within_limit: boolean;
  body_digest: string;
  body_bytes: string;
  observed_at_unix: string;
  observed_at_iso: string;
  provenance: string;
}

export interface BondView extends BondSummary {
  endpoint_url: string;
  expected_status: string;
  proof_token: string;
  accept_by_unix: string;
  starts_at_unix: string;
  ends_at_unix: string;
  interval_secs: string;
  slot_count: string;
  min_observations: string;
  max_failures: string;
  created_at_unix: string;
  created_at_iso: string;
  accepted_at_unix: string;
  accepted_at_iso: string;
  readiness: ReadinessRecord;
  uptime_bps: string;
  current_slot: string;
  current_slot_recorded: boolean;
  can_observe: boolean;
  can_finalize: boolean;
  can_expire: boolean;
  cancellation_requested: boolean;
  cancellation_requested_by: string;
  result: string;
  settled_at_unix: string;
  settled_at_iso: string;
  payout_recipient: string;
  payout_atto: string;
}

export interface ProtocolStats {
  total_created: string;
  total_finalized: string;
  total_met: string;
  total_breached: string;
  total_inconclusive: string;
  total_locked_atto: string;
  total_returned_to_providers_atto: string;
  total_paid_to_beneficiaries_atto: string;
  fee_bps: string;
  admin_controls: boolean;
  experimental: boolean;
  max_page_size: string;
  max_response_bytes: string;
  probe_policy: string;
  version: string;
}

export interface CreateBondInput {
  serviceName: string;
  endpointUrl: string;
  beneficiary: Address;
  expectedStatus: number;
  proofToken: string;
  acceptByUnix: number;
  startsAtUnix: number;
  intervalSecs: number;
  slotCount: number;
  minObservations: number;
  maxFailures: number;
  bondAtto: bigint;
}

export interface TxProgress {
  state: "awaiting-signature" | "submitted" | "finalizing" | "confirmed" | "failed";
  label: string;
  hash?: string;
}

export const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_UPTIMEBOND_ADDRESS ?? "";
export const NETWORK_NAME = process.env.NEXT_PUBLIC_NETWORK_NAME ?? "StudioNet";
export const CONTRACT_READY = /^0x[0-9a-fA-F]{40}$/.test(CONTRACT_ADDRESS) && !/^0x0{40}$/i.test(CONTRACT_ADDRESS);
export const CONTRACT_EXPLORER_URL = CONTRACT_READY
  ? `https://explorer-studio.genlayer.com/address/${CONTRACT_ADDRESS}`
  : "https://explorer-studio.genlayer.com";

const readClient = createClient({ chain: chains.studionet });
const readRetryDelays = [350, 1000] as const;

function contractAddress(): Address {
  if (!CONTRACT_READY) throw new Error("UptimeBond has not been configured for this environment.");
  return CONTRACT_ADDRESS as Address;
}

export function formatGen(attoValue: string | bigint, precision = 4): string {
  const atto = typeof attoValue === "bigint" ? attoValue : BigInt(attoValue || "0");
  const whole = atto / 10n ** 18n;
  const fraction = (atto % 10n ** 18n).toString().padStart(18, "0").slice(0, precision).replace(/0+$/, "");
  return fraction ? `${whole}.${fraction}` : whole.toString();
}

export function parseGen(value: string): bigint {
  const trimmed = value.trim();
  if (!/^\d+(\.\d{0,18})?$/.test(trimmed)) throw new Error("Enter a valid GEN amount with at most 18 decimal places.");
  const [whole, fraction = ""] = trimmed.split(".");
  return BigInt(whole) * 10n ** 18n + BigInt(fraction.padEnd(18, "0"));
}

export function isAddress(value: string): value is Address {
  return /^0x[0-9a-fA-F]{40}$/.test(value) && !/^0x0{40}$/i.test(value);
}

export function isPublicHttpsEndpoint(value: string): boolean {
  const source = value.trim();
  if (source.length < 12 || source.length > 360 || /\s|\0/.test(source)) return false;
  if (!/^https:\/\/[^/]+(?:\/.*)?$/.test(source)) return false;
  const authority = source.slice(8).split("/", 1)[0];
  if (!authority || /@|\[|\]/.test(authority)) return false;
  const [rawHost, port] = authority.split(":", 2);
  if (port !== undefined && (!/^\d{1,5}$/.test(port) || Number(port) > 65535)) return false;
  const host = rawHost.toLowerCase().replace(/\.$/, "");
  if (!host.includes(".") || host === "localhost" || host.endsWith(".local")) return false;
  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) return false;
  return /^[a-z0-9.-]+$/.test(host) && !host.includes("..");
}

export function isProofToken(value: string): boolean {
  return /^[A-Za-z0-9._:/-]{8,96}$/.test(value.trim());
}

export function shortenAddress(value: string): string {
  return value.length > 12 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value;
}

export function friendlyError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  const expected = message.match(/\[EXPECTED\]\s*([^"\n]+)/);
  if (expected?.[1]) return expected[1].trim();
  if (/rejected|denied|cancelled/i.test(message)) return "The wallet request was cancelled.";
  if (/wrong chain|configured for chain/i.test(message)) return `Switch your wallet to ${NETWORK_NAME} and try again.`;
  if (/failed to fetch|fetch failed|network error|econn|socket hang up|service unavailable|\b(?:502|503|504)\b/i.test(message)) {
    return "StudioNet or the health endpoint is temporarily unreachable. Check the transaction before retrying.";
  }
  if (/timeout|timed out/i.test(message)) return "Confirmation is taking longer than expected. Check the transaction before retrying.";
  return message.length > 220 ? `${message.slice(0, 217)}…` : message;
}

export function isTransientReadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return /failed to fetch|fetch failed|network error|timeout|timed out|econn|socket hang up|service unavailable|\b(?:502|503|504)\b/i.test(message);
}

export async function withReadRetry<T>(
  operation: () => Promise<T>,
  wait: (delayMs: number) => Promise<void> = (delayMs) => new Promise((resolve) => setTimeout(resolve, delayMs)),
): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try { return await operation(); }
    catch (error) {
      if (!isTransientReadError(error) || attempt >= readRetryDelays.length) throw error;
      await wait(readRetryDelays[attempt]);
    }
  }
}

export async function connectWallet(wallet: WalletOption): Promise<WalletSession> {
  const address = await connectStudioWallet(wallet.provider);
  return {
    address,
    client: createClient({ chain: chains.studionet, account: address, provider: wallet.provider as never }),
    provider: wallet.provider,
    walletName: wallet.name,
  };
}

async function waitForSuccess(hash: unknown, onProgress: (progress: TxProgress) => void): Promise<void> {
  const txHash = String(hash);
  onProgress({ state: "finalizing", label: "GenLayer validators are finalizing the transaction", hash: txHash });
  const receipt = await readClient.waitForTransactionReceipt({ hash: hash as never, status: TransactionStatus.FINALIZED, retries: 120 });
  assertSuccessfulExecution(receipt);
  onProgress({ state: "confirmed", label: "Confirmed by GenLayer validators", hash: txHash });
}

async function write(
  session: WalletSession,
  functionName: string,
  args: unknown[],
  value: bigint,
  onProgress: (progress: TxProgress) => void,
): Promise<string> {
  return oneTransactionAtATime(session.address, async () => {
    let txHash: string | undefined;
    onProgress({ state: "awaiting-signature", label: "Confirm this transaction in your wallet" });
    try {
      const hash = await session.client.writeContract({ address: contractAddress(), functionName, args: args as never[], value });
      txHash = String(hash);
      onProgress({ state: "submitted", label: "Transaction submitted", hash: txHash });
      await waitForSuccess(hash, onProgress);
      return txHash;
    } catch (error) {
      onProgress({ state: "failed", label: friendlyError(error), hash: txHash });
      throw error;
    }
  });
}

export async function listBonds(): Promise<BondSummary[]> {
  const first = await withReadRetry(() => readClient.readContract({ address: contractAddress(), functionName: "list_bonds", args: [0, 25] })) as unknown as { total: string; items: BondSummary[] };
  const total = Number(first.total);
  if (!Number.isSafeInteger(total) || total < 0) throw new Error("The contract returned an invalid bond count.");
  const page = total > 25
    ? await withReadRetry(() => readClient.readContract({ address: contractAddress(), functionName: "list_bonds", args: [total - 25, 25] })) as unknown as { items: BondSummary[] }
    : first;
  return [...page.items].reverse();
}

export async function getBond(bondId: string): Promise<BondView> {
  return await withReadRetry(() => readClient.readContract({ address: contractAddress(), functionName: "get_bond", args: [bondId] })) as unknown as BondView;
}

export async function getObservations(bondId: string): Promise<ObservationRecord[]> {
  const result = await withReadRetry(() => readClient.readContract({ address: contractAddress(), functionName: "get_observations", args: [bondId] })) as unknown as { items: ObservationRecord[] };
  return result.items;
}

export async function getStats(): Promise<ProtocolStats> {
  return await withReadRetry(() => readClient.readContract({ address: contractAddress(), functionName: "get_stats", args: [] })) as unknown as ProtocolStats;
}

export const createBond = (session: WalletSession, input: CreateBondInput, onProgress: (progress: TxProgress) => void) =>
  write(session, "create_bond", [
    input.serviceName,
    input.endpointUrl,
    input.beneficiary,
    input.expectedStatus,
    input.proofToken,
    input.acceptByUnix,
    input.startsAtUnix,
    input.intervalSecs,
    input.slotCount,
    input.minObservations,
    input.maxFailures,
  ], input.bondAtto, onProgress);

export const verifyReadiness = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "verify_readiness", [bondId], 0n, onProgress);
export const acceptBond = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "accept_bond", [bondId], 0n, onProgress);
export const declineBond = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "decline_bond", [bondId], 0n, onProgress);
export const cancelOffer = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "cancel_offer", [bondId], 0n, onProgress);
export const expireOffer = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "expire_offer", [bondId], 0n, onProgress);
export const requestCancellation = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "request_cancellation", [bondId], 0n, onProgress);
export const withdrawCancellation = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "withdraw_cancellation_request", [bondId], 0n, onProgress);
export const recordObservation = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "record_observation", [bondId], 0n, onProgress);
export const finalizeBond = (session: WalletSession, bondId: string, onProgress: (progress: TxProgress) => void) => write(session, "finalize_bond", [bondId], 0n, onProgress);
