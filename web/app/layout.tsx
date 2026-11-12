import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";

// Self-hosted so builds don't fetch from Google Fonts; see fonts/README.md.
const figtree = localFont({
  variable: "--font-figtree",
  src: "./fonts/figtree-latin-wght-normal.woff2",
  weight: "300 900",
});

const ibmPlexMono = localFont({
  variable: "--font-ibm-plex-mono",
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
  ],
});

const sourceSerif = localFont({
  variable: "--font-source-serif",
  src: "./fonts/source-serif-4-latin-wght-normal.woff2",
  weight: "200 900",
});

const fraunces = localFont({
  variable: "--font-fraunces",
  src: "./fonts/fraunces-latin-wght-normal.woff2",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Hecate Lab · Cost–Quality Routing for Real-World SWE Tasks",
  description:
    "Hecate Lab routes models on complex, near–real-world software engineering tasks — balancing cost and quality with a near-real-world task pipeline and ts-repo-metrics for objective code quality.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${figtree.variable} ${ibmPlexMono.variable} ${sourceSerif.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="relative flex min-h-full flex-col bg-background font-sans text-foreground">
        {children}
      </body>
    </html>
  );
}
