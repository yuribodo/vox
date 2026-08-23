import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/instrument-sans/index.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://yuribodo.github.io/vox/"),
  title: "Vox — voice in, text out, nothing leaves",
  description:
    "Open-source push-to-talk dictation for Linux, transcribed locally on your machine.",
  openGraph: {
    title: "Vox — voice in, text out, nothing leaves",
    description: "Open-source push-to-talk dictation for Linux, transcribed locally.",
    type: "website",
    url: "https://yuribodo.github.io/vox/",
    images: [
      {
        url: "https://yuribodo.github.io/vox/images/voice-specimen.webp",
        width: 1536,
        height: 1024,
        alt: "A disassembled microphone and circuit board arranged as a technical voice specimen",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: ["https://yuribodo.github.io/vox/images/voice-specimen.webp"],
  },
};

export const viewport: Viewport = {
  themeColor: "#2850e7",
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
