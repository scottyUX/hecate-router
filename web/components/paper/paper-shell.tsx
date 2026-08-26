import Link from "next/link";
import type { ReactNode } from "react";

export type PaperTocItem = {
  href: string;
  label: string;
  children?: { href: string; label: string }[];
};

export function PaperShell({
  title,
  authors,
  affiliations,
  date,
  subjects,
  updated,
  tags,
  toc,
  children,
}: {
  title: string;
  authors: ReactNode;
  affiliations: string;
  date: string;
  subjects: string[];
  updated: string;
  tags: string;
  toc: PaperTocItem[];
  children: ReactNode;
}) {
  return (
    <div className="paper">
      <header className="bg-[var(--paper-accent)] text-white">
        <div className="mx-auto flex h-14 w-full max-w-[1270px] items-center justify-between px-3 md:px-4">
          <Link
            href="/"
            className="font-sans text-[15px] font-medium tracking-tight text-white/92 no-underline hover:text-white hover:no-underline"
          >
            Hecate Lab
          </Link>
          <Link
            href="/journal"
            className="font-sans text-[15px] text-white/92 no-underline hover:text-white hover:no-underline"
          >
            Journal
          </Link>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-[1270px] items-start gap-8 px-3 py-8 md:px-4 lg:grid-cols-[minmax(0,823px)_minmax(0,400px)] lg:justify-between">
        <article className="min-w-0">
          <h1 className="font-display text-[2.35rem] leading-[1.25] font-semibold tracking-tight text-[var(--paper-ink)]">
            {title}
          </h1>
          <p className="mt-4 text-lg leading-[1.5] text-[var(--paper-muted)]">
            {authors}
          </p>
          <p className="mt-1 text-lg leading-[1.5] text-[var(--paper-muted)]">
            {affiliations}
          </p>
          <p className="mt-3 text-lg text-[var(--paper-ink)]">{date}</p>
          <hr className="mt-4 border-[var(--paper-line)]" />
          {children}
        </article>

        <aside className="space-y-4 font-sans lg:sticky lg:top-6">
          <div className="rounded-xl border border-[var(--paper-line)] bg-[var(--paper-card)] p-4">
            <p className="text-xs font-medium tracking-wide text-[var(--paper-muted)] uppercase">
              Subjects
            </p>
            <ul className="mt-2 space-y-1 text-sm font-medium text-[var(--paper-ink)]">
              {subjects.map((subject) => (
                <li key={subject}>{subject}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-[var(--paper-line)] bg-[var(--paper-card)] p-4">
            <p className="text-xs font-medium tracking-wide text-[var(--paper-muted)] uppercase">
              Updated
            </p>
            <p className="mt-2 text-sm text-[var(--paper-ink)]">{updated}</p>
            <p className="mt-3 text-xs text-[var(--paper-muted)]">{tags}</p>
          </div>
          <nav className="hidden rounded-xl border border-[var(--paper-line)] bg-[var(--paper-card)] p-4 lg:block">
            <p className="text-xs font-medium tracking-wide text-[var(--paper-muted)] uppercase">
              Contents
            </p>
            <ol className="mt-2 space-y-1 text-sm">
              {toc.map((item, index) => (
                <li key={item.href}>
                  <a href={item.href} className="no-underline hover:underline">
                    {index + 1} {item.label}
                  </a>
                  {item.children ? (
                    <ol className="mt-1 ml-3 space-y-1 text-[13px]">
                      {item.children.map((child, childIndex) => (
                        <li key={child.href}>
                          <a
                            href={child.href}
                            className="no-underline hover:underline"
                          >
                            {index + 1}.{childIndex + 1} {child.label}
                          </a>
                        </li>
                      ))}
                    </ol>
                  ) : null}
                </li>
              ))}
            </ol>
          </nav>
        </aside>
      </div>
    </div>
  );
}

export function PaperAbstract({ children }: { children: ReactNode }) {
  return (
    <section
      id="abstract"
      className="mt-6 scroll-mt-8 rounded-xl border border-[var(--paper-line)] bg-[var(--paper-card)] px-[17.6px] py-4"
    >
      <h2 className="font-serif text-2xl font-bold text-[#333]">Abstract</h2>
      <div className="mt-2 space-y-3 text-[15px] leading-[1.5] text-[var(--paper-ink)]">
        {children}
      </div>
    </section>
  );
}

export function PaperToc({ items }: { items: PaperTocItem[] }) {
  return (
    <nav
      id="TOC"
      className="mt-4 rounded-xl border border-[var(--paper-line)] bg-[var(--paper-card)] px-[17.6px] py-4 font-sans"
    >
      <ol className="space-y-1 text-[15px]">
        {items.map((item, index) => (
          <li key={item.href}>
            <a href={item.href} className="no-underline hover:underline">
              {index + 1} {item.label}
            </a>
            {item.children ? (
              <ol className="mt-1 ml-4 space-y-1 text-sm">
                {item.children.map((child, childIndex) => (
                  <li key={child.href}>
                    <a href={child.href} className="no-underline hover:underline">
                      {index + 1}.{childIndex + 1} {child.label}
                    </a>
                  </li>
                ))}
              </ol>
            ) : null}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function PaperSection({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mt-12 scroll-mt-8">
      <h2 className="font-serif text-[2.5rem] leading-[1.2] font-medium text-[#333]">
        {number} {title}
      </h2>
      <div className="mt-4 space-y-4 text-lg leading-[1.5]">{children}</div>
    </section>
  );
}

export function PaperSubsection({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mt-10 scroll-mt-8">
      <h3 className="font-serif text-[2rem] leading-[1.2] font-medium text-[#333]">
        {number} {title}
      </h3>
      <div className="mt-3 space-y-4 text-lg leading-[1.5]">{children}</div>
    </section>
  );
}
