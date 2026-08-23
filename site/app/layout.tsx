import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/geist/index.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://yuribodo.github.io/vox/"),
  title: "Vox — local push-to-talk for Linux",
  description:
    "Open-source push-to-talk dictation for Linux. Your voice is transcribed locally and returned to your cursor.",
  openGraph: {
    title: "Vox — speak anywhere, send nowhere",
    description: "Open-source push-to-talk dictation that stays on your Linux machine.",
    type: "website",
    url: "https://yuribodo.github.io/vox/",
    images: [
      {
        url: "https://yuribodo.github.io/vox/images/resonance.webp",
        width: 1536,
        height: 1024,
        alt: "An acoustic diaphragm turning a pressure wave into a precise signal",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: ["https://yuribodo.github.io/vox/images/resonance.webp"],
  },
};

export const viewport: Viewport = {
  themeColor: "#080907",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
