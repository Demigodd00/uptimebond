import { ImageResponse } from "next/og";

export const alt = "UptimeBond by demigodd00";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 70, background: "#07110f", color: "#edf7f2", fontFamily: "Arial" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 30 }}><div style={{ width: 54, height: 54, borderRadius: 15, background: "#91f2bd", color: "#07110f", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900 }}>⌁</div>UptimeBond <span style={{ color: "#789087" }}>by demigodd00</span></div>
      <div style={{ display: "flex", flexDirection: "column" }}><span style={{ color: "#91f2bd", fontSize: 24, letterSpacing: 4 }}>GENLAYER STUDIONET</span><strong style={{ marginTop: 20, fontSize: 92, lineHeight: 1 }}>Put uptime<br />on the line.</strong></div>
      <div style={{ display: "flex", justifyContent: "space-between", color: "#9dafaa", fontSize: 24 }}><span>Fixed checks · exact evidence · contract settlement</span><span>Test GEN</span></div>
    </div>,
    size,
  );
}
