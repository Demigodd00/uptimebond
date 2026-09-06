"use client";

import AppShell from "@/components/AppShell";
import BondBoard from "@/components/BondBoard";
import { useWallet } from "@/components/WalletProvider";

export default function BondsPage() {
  const { session } = useWallet();
  return <AppShell><BondBoard session={session} /></AppShell>;
}
