import type { Metadata } from "next";
import AppShell from "@/components/AppShell";
import HowItWorks from "@/components/HowItWorks";

export const metadata: Metadata = { title: "How it works", alternates: { canonical: "/how-it-works" } };

export default function HowPage() {
  return <AppShell><HowItWorks /></AppShell>;
}
