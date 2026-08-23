import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/manrope/index.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://yuribodo.github.io/vox/"),
  title: "Vox — local voice-to-text for Linux",
  description:
    "Open-source push-to-talk dictation for Linux. Transcribe locally and return text directly to your cursor.",
  openGraph: {
    title: "Vox — dictate anywhere, keep it local",
    description: "Open-source voice-to-text that runs on your Linux machine.",
    type: "website",
    url: "https://yuribodo.github.io/vox/",
  },
  twitter: {
    card: "summary",
    title: "Vox — local voice-to-text for Linux",
    description: "Open-source voice-to-text that runs on your Linux machine.",
  },
};

export const viewport: Viewport = {
  themeColor: "#0c0e12",
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
