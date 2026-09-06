import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "UptimeBond by demigodd00",
    short_name: "UptimeBond",
    description: "Validator-settled public endpoint bonds on GenLayer StudioNet.",
    start_url: "/",
    display: "standalone",
    background_color: "#07110f",
    theme_color: "#91f2bd",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
