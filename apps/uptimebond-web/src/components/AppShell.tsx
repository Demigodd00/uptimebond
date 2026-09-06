"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CONTRACT_READY } from "@/lib/contract";
import WalletButton from "./WalletButton";
import { useWallet } from "./WalletProvider";

const routes = [
  { href: "/bonds", label: "Bonds" },
  { href: "/bonds/new", label: "Create bond" },
  { href: "/how-it-works", label: "How it works" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { error } = useWallet();
  const active = (href: string) => href === "/bonds" ? pathname === href : pathname.startsWith(href);

  return (
    <>
      <main>
        <div className="site-shell">
          <nav className="topbar" aria-label="Primary navigation">
            <Link className="brand" href="/" aria-label="UptimeBond home">
              <span className="brand-mark"><i /></span>
              <span>UptimeBond<small>by demigodd00</small></span>
            </Link>
            <div className="topbar-links">
              <Link className={pathname === "/status" ? "active" : ""} href="/status">Protocol status</Link>
            </div>
            <WalletButton />
          </nav>
          <div className="network-banner" role="note">
            <strong>{CONTRACT_READY ? "StudioNet live" : "Preview mode"}</strong>
            <span>Test GEN has no monetary value</span>
            <span>· static health endpoints only</span>
          </div>
          <nav className="workspace-tabs" aria-label="UptimeBond workspace">
            {routes.map((route) => (
              <Link className={active(route.href) ? "active" : ""} href={route.href} key={route.href}>{route.label}</Link>
            ))}
          </nav>
          {error ? <p className="form-error wallet-error" role="alert">{error}</p> : null}
          {children}
        </div>
      </main>
      <footer>
        <div className="site-shell footer-inner">
          <Link className="brand" href="/"><span className="brand-mark"><i /></span><span>UptimeBond<small>by demigodd00 · StudioNet</small></span></Link>
          <p>Public endpoint bonds. Validator-settled.</p>
          <Link href="/status">Contract status →</Link>
        </div>
      </footer>
    </>
  );
}
