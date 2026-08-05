import type { Metadata } from "next";
import { Figtree, IBM_Plex_Mono } from "next/font/google";

import "./globals.css";

const figtree = Figtree({
  variable: "--font-figtree",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
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
      className={`${figtree.variable} ${ibmPlexMono.variable} h-full antialiased`}
    >
      <body className="relative flex min-h-full flex-col bg-background font-sans text-foreground">
        {children}
      </body>
    </html>
  );
}
