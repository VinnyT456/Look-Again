import type { Metadata, Viewport } from "next";
import { Schibsted_Grotesk } from "next/font/google";

import { AppShell } from "@/components/shell";

import "./globals.css";

const grotesk = Schibsted_Grotesk({ subsets: ["latin"], variable: "--font-grotesk", display: "swap" });

export const metadata: Metadata = {
  title: { default: "WildcatVerify", template: "%s · WildcatVerify" },
  description: "Check whether a photo on Bluesky is real, edited, or AI-generated, and learn the clues to spot fakes yourself.",
  applicationName: "WildcatVerify",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#2e1d4d" },
    { media: "(prefers-color-scheme: dark)", color: "#1e1433" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={grotesk.variable}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
