import type { TxProgress } from "./contract";
import type { EthereumProvider } from "./wallet";

export function transactionPending(progress: TxProgress | null): boolean {
  return progress !== null && ["awaiting-signature", "submitted", "finalizing"].includes(progress.state);
}

export function bondShareUrl(origin: string, bondId: string): string {
  const url = new URL("/bonds", origin);
  url.searchParams.set("bond", bondId);
  return url.toString();
}

export function formatCountdown(unix: string, now: number): string {
  const seconds = Math.max(0, Math.ceil(Number(unix) - now));
  if (seconds === 0) return "Now";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  return hours >= 24 ? `${Math.floor(hours / 24)}d ${hours % 24}h` : `${hours}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function formatPercent(basisPoints: string): string {
  const value = Number(basisPoints);
  if (!Number.isFinite(value)) return "—";
  return `${(value / 100).toFixed(value % 100 === 0 ? 0 : 2)}%`;
}

export function roleFor(address: string | undefined, provider: string, beneficiary: string): "provider" | "beneficiary" | "observer" {
  if (!address) return "observer";
  if (address.toLowerCase() === provider.toLowerCase()) return "provider";
  if (address.toLowerCase() === beneficiary.toLowerCase()) return "beneficiary";
  return "observer";
}

const statusSyncDelays = [400, 1100] as const;

export async function rereadUntilStatusMatches<T extends { status: string }>(
  initial: T,
  expectedStatus: string | undefined,
  read: () => Promise<T>,
  wait: (delayMs: number) => Promise<void> = (delayMs) => new Promise((resolve) => setTimeout(resolve, delayMs)),
): Promise<T> {
  if (!expectedStatus || initial.status === expectedStatus) return initial;
  let latest = initial;
  for (const delay of statusSyncDelays) {
    await wait(delay);
    latest = await read();
    if (latest.status === expectedStatus) break;
  }
  return latest;
}

export function watchWalletSession(provider: EthereumProvider | undefined, address: string | undefined, reset: () => void): () => void {
  if (!provider?.on || !address) return () => {};
  const accountsChanged = (...args: unknown[]) => {
    const accounts = args[0];
    if (!Array.isArray(accounts) || typeof accounts[0] !== "string" || accounts[0].toLowerCase() !== address.toLowerCase()) reset();
  };
  provider.on("accountsChanged", accountsChanged);
  provider.on("chainChanged", reset);
  provider.on("disconnect", reset);
  return () => {
    provider.removeListener?.("accountsChanged", accountsChanged);
    provider.removeListener?.("chainChanged", reset);
    provider.removeListener?.("disconnect", reset);
  };
}

const activeTransactions = new Set<string>();

export async function oneTransactionAtATime<T>(account: string, action: () => Promise<T>): Promise<T> {
  const key = account.toLowerCase();
  if (activeTransactions.has(key)) throw new Error("A transaction is already in progress. Wait for confirmation.");
  activeTransactions.add(key);
  try {
    return await action();
  } finally {
    activeTransactions.delete(key);
  }
}
