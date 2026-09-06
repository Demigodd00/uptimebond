import type { Metadata, Viewport } from "next";
import { WalletProvider } from "@/components/WalletProvider";
import { getSiteUrl } from "@/lib/site-url";
import "./globals.css";

const appUrl = getSiteUrl();

export const metadata: Metadata = {
  metadataBase: new URL(appUrl),
  title: { default: "UptimeBond by demigodd00", template: "%s · UptimeBond" },
  description: "Public HTTP performance bonds settled by GenLayer validators on StudioNet.",
  applicationName: "UptimeBond",
  authors: [{ name: "demigodd00" }],
  creator: "demigodd00",
  icons: { icon: "/icon.svg" },
  manifest: "/manifest.webmanifest",
  openGraph: {
    type: "website",
    url: "/",
    siteName: "UptimeBond",
    title: "UptimeBond by demigodd00",
    description: "Lock a performance bond. Let GenLayer validators check the endpoint and settle it.",
  },
  twitter: {
    card: "summary_large_image",
    title: "UptimeBond by demigodd00",
    description: "Validator-settled public endpoint bonds on GenLayer StudioNet.",
  },
  category: "technology",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#07110f" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><WalletProvider>{children}</WalletProvider></body></html>;
}
