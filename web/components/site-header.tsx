import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "#program", label: "Program" },
  { href: "#architecture", label: "Architecture" },
  { href: "#roadmap", label: "Milestones" },
  { href: "/journal", label: "Journal" },
  { href: "/profile", label: "Profile" },
] as const;

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-border/80 bg-background/90 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-4 px-5 py-3.5 md:px-8">
        <Link
          href="#top"
          className="flex items-center gap-2 text-[1.05rem] font-medium tracking-tight text-foreground"
        >
          <span className="text-primary" aria-hidden="true">
            ●
          </span>
          <span>Hecate Lab</span>
        </Link>
        <div className="flex items-center gap-3 sm:gap-6">
          <nav
            className="hidden items-center gap-5 text-sm text-foreground/80 lg:flex"
            aria-label="Primary"
          >
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="transition-colors hover:text-primary"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <Link
            href="/login?next=/journal"
            className={cn(
              buttonVariants({ size: "sm", variant: "outline" }),
              "h-9 rounded-full border-border px-4 text-sm font-medium"
            )}
          >
            Login
          </Link>
        </div>
      </div>
    </header>
  );
}
