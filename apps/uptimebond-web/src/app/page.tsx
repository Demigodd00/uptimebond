import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import UptimeBondApp from "@/components/UptimeBondApp";

export const metadata: Metadata = { alternates: { canonical: "/" } };

export default function Home() {
  return <AppShell><UptimeBondApp /></AppShell>;
}
