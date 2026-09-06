"use client";

import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import CreateBond from "@/components/CreateBond";
import { useWallet } from "@/components/WalletProvider";

export default function NewBondPage() {
  const { session } = useWallet();
  const router = useRouter();
  return <AppShell><CreateBond session={session} onCreated={() => router.prefetch("/bonds")} /></AppShell>;
}
