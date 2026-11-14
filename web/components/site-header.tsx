import Link from "next/link";

import { HecateMark } from "@/components/hecate-mark";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Research" },
  { href: "/people", label: "People" },
  { href: "/publications", label: "Publications" },
  { href: "/events", label: "Events" },
  { href: "/journal", label: "Journal" },
] as const;

export function SiteHeader({ current = "/" }: { current?: string }) {
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--hc-rule)] bg-[var(--hc-bg)]/90 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-4 px-5 py-3.5 md:px-8">
        <Link
          href="/"
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
            className="hidden items-center gap-5 text-sm font-medium text-[var(--hc-body)] md:flex"
            aria-label="Primary"
          >
            {navLinks.map((link) => {
              const active = link.href === current;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "border-b-2 py-1 transition-colors hover:text-[var(--hc-accent)]",
                    active
                      ? "border-[var(--hc-accent)] text-[var(--hc-ink)]"
                      : "border-transparent"
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
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
      <nav
        className="flex gap-5 overflow-x-auto [scrollbar-width:none] border-t border-[var(--hc-rule)] px-5 py-2 text-sm font-medium text-[var(--hc-body)] md:hidden"
        aria-label="Primary"
      >
        {navLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            aria-current={link.href === current ? "page" : undefined}
            className={cn(
              "shrink-0",
              link.href === current && "text-[var(--hc-ink)] underline decoration-[var(--hc-accent)] decoration-2 underline-offset-4"
            )}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
