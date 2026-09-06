import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import StatusDashboard from "@/components/StatusDashboard";

export const metadata: Metadata = { title: "Protocol status", alternates: { canonical: "/status" } };

export default function StatusPage() {
  return <AppShell><StatusDashboard /></AppShell>;
}
