import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";

// Self-hosted so builds don't fetch from Google Fonts; see fonts/README.md.
const figtree = localFont({
  variable: "--font-figtree",
  src: "./fonts/figtree-latin-wght-normal.woff2",
  weight: "300 900",
});

const inter = localFont({
  variable: "--font-inter",
  src: "./fonts/inter-latin-wght-normal.woff2",
  weight: "100 900",
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
  title: "Hecate Lab · When should a coding agent call the frontier model?",
  description:
    "Hecate Lab at UC Santa Cruz studies when a cheap coding agent can finish a software-engineering task on its own and when it needs a frontier model, using execution-grounded labels and pre-registered experiments.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${figtree.variable} ${inter.variable} ${ibmPlexMono.variable} ${sourceSerif.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="relative flex min-h-full flex-col bg-background font-sans text-foreground">
        {children}
      </body>
    </html>
  );
}
