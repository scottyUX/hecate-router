import { AuthRedirectHandler } from "@/components/auth-redirect-handler";
import { HecateMark } from "@/components/hecate-mark";
import { SiteHeader } from "@/components/site-header";

export function SiteFooter() {
  return (
    <footer className="bg-[var(--hc-ink)] px-5 pb-10 text-xs text-[var(--hc-faint)] md:px-8">
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-2 border-t border-white/15 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2">
          <HecateMark className="size-4 text-white" />
          Hecate Lab · UC Santa Cruz
        </p>
        <p>MIT License</p>
      </div>
    </footer>
  );
}

/** Header, themed body and footer shared by the public pages. */
export function SiteShell({
  current,
  children,
}: {
  current?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="hecate-site flex min-h-full flex-1 flex-col">
      <AuthRedirectHandler />
      <SiteHeader current={current} />
      <main id="top" className="flex-1">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

/** Title block at the top of an inner page. */
export function PageIntro({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="border-b border-[var(--hc-rule)] pb-10">
      <h1 className="text-5xl leading-none font-bold tracking-[-0.04em] text-[var(--hc-ink)] md:text-7xl">
        {title}
      </h1>
      {children ? (
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--hc-body)]">{children}</p>
      ) : null}
    </div>
  );
}
