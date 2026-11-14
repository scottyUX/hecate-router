import Link from "next/link";

import { HecateMark } from "@/components/hecate-mark";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "#gap", label: "The gap" },
  { href: "#program", label: "Questions" },
  { href: "#architecture", label: "How it works" },
  { href: "#roadmap", label: "Roadmap" },
  { href: "/journal", label: "Journal" },
  { href: "/profile", label: "Profile" },
] as const;

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--hc-rule)] bg-[var(--hc-bg)]/90 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-4 px-5 py-3.5 md:px-8">
        <Link
          href="#top"
          className="flex items-center gap-2 text-[1.35rem] leading-none font-bold tracking-[-0.04em] text-[var(--hc-ink)]"
        >
          <HecateMark className="size-6" />
          <span>hecate</span>
          <span className="ml-0.5 text-[11px] font-semibold tracking-[0.14em] text-[var(--hc-muted)] uppercase">
            Lab
          </span>
        </Link>
        <div className="flex items-center gap-3 sm:gap-6">
          <nav
            className="hidden items-center gap-5 text-sm font-medium text-[var(--hc-body)] lg:flex"
            aria-label="Primary"
          >
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="transition-colors hover:text-[var(--hc-accent)]"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <Link
            href="/login?next=/journal"
            className={cn(
              buttonVariants({ size: "sm", variant: "outline" }),
              "h-9 rounded-full border-[var(--hc-ink)] bg-transparent px-4 text-sm font-semibold text-[var(--hc-ink)] hover:bg-[var(--hc-ink)] hover:text-[var(--hc-bg)]"
            )}
          >
            Login
          </Link>
        </div>
      </div>
    </header>
  );
}
