import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://yuribodo.github.io/vox/"),
  title: "Vox — Local Linux dictation",
  description:
    "Vox is private, local push-to-talk dictation for Linux. Speak, review, then send.",
  openGraph: {
    title: "Vox — voice to text, on your machine",
    description: "Private, local push-to-talk dictation for Linux.",
    type: "website",
    url: "https://yuribodo.github.io/vox/",
  },
  twitter: { card: "summary" },
};

export const viewport: Viewport = {
  themeColor: "#070806",
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
