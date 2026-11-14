"use client";

import { ArrowUpRight } from "lucide-react";
import { useMemo, useState } from "react";

import type { Publication } from "@/lib/lab";

const selectClass =
  "h-10 w-full rounded-sm border border-[var(--hc-rule)] bg-[var(--hc-bg)] px-3 text-sm text-[var(--hc-ink)] focus:border-[var(--hc-ink)] focus:outline-none";

function citation(p: Publication) {
  const status = p.status ? ` (${p.status})` : "";
  return `${p.authors.join(", ")}. "${p.title}." ${p.venue}, ${p.year}${status}.`;
}

export function PublicationsList({ publications }: { publications: Publication[] }) {
  const [query, setQuery] = useState("");
  const [year, setYear] = useState("all");
  const [type, setType] = useState("all");
  const [newestFirst, setNewestFirst] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);

  const years = useMemo(
    () => [...new Set(publications.map((p) => p.year))].sort((a, b) => b - a),
    [publications]
  );
  const types = useMemo(() => [...new Set(publications.map((p) => p.type))], [publications]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return publications
      .filter((p) => year === "all" || String(p.year) === year)
      .filter((p) => type === "all" || p.type === type)
      .filter(
        (p) =>
          !q ||
          [p.title, p.venue, ...p.authors, ...p.topics].join(" ").toLowerCase().includes(q)
      )
      .sort((a, b) => (newestFirst ? b.year - a.year : a.year - b.year));
  }, [publications, query, year, type, newestFirst]);

  if (publications.length === 0) {
    return (
      <div className="mt-12 rounded-sm border border-dashed border-[var(--hc-faint)] px-6 py-16 text-center">
        <p className="text-lg font-bold tracking-[-0.02em] text-[var(--hc-ink)]">
          Papers are on the way
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--hc-body)]">
          Work under review stays anonymous until it’s accepted. Published papers
          will be listed here.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="mt-10 grid gap-3 rounded-sm border border-[var(--hc-rule)] p-4 md:grid-cols-[2fr_1fr_1fr_1fr]">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search title, author or topic"
          aria-label="Search publications"
          className={selectClass}
        />
        <select aria-label="Year" value={year} onChange={(e) => setYear(e.target.value)} className={selectClass}>
          <option value="all">All years</option>
          {years.map((y) => (
            <option key={y} value={String(y)}>
              {y}
            </option>
          ))}
        </select>
        <select aria-label="Type" value={type} onChange={(e) => setType(e.target.value)} className={selectClass}>
          <option value="all">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort"
          value={newestFirst ? "new" : "old"}
          onChange={(e) => setNewestFirst(e.target.value === "new")}
          className={selectClass}
        >
          <option value="new">Newest first</option>
          <option value="old">Oldest first</option>
        </select>
      </div>

      <ol className="mt-6">
        {shown.map((p) => (
          <li key={p.title} className="border-b border-[var(--hc-rule)] py-8">
            <p className="flex flex-wrap items-center gap-2 font-mono text-xs tracking-[0.08em] text-[var(--hc-muted)] uppercase">
              <span>{p.year}</span>
              <span>· {p.type}</span>
              {p.status ? (
                <span className="rounded-full border border-[var(--hc-rule)] px-2 py-0.5 normal-case tracking-normal">
                  {p.status}
                </span>
              ) : null}
            </p>
            <h2 className="mt-3 text-xl leading-snug font-bold tracking-[-0.02em] text-[var(--hc-ink)]">
              {p.title}
            </h2>
            <p className="mt-2 text-sm text-[var(--hc-body)]">{p.authors.join(", ")}</p>
            <p className="text-sm text-[var(--hc-muted)] italic">{p.venue}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {p.topics.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-[#e6e3dc] px-2.5 py-0.5 text-xs text-[var(--hc-body)]"
                >
                  {t}
                </span>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-4 text-sm font-semibold">
              {p.pdf ? (
                <a href={p.pdf} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:underline">
                  PDF <ArrowUpRight className="size-3.5" aria-hidden="true" />
                </a>
              ) : null}
              {p.link ? (
                <a href={p.link.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:underline">
                  {p.link.label} <ArrowUpRight className="size-3.5" aria-hidden="true" />
                </a>
              ) : null}
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(citation(p)).then(
                    () => setCopied(p.title),
                    () => setCopied(null)
                  );
                }}
                className="text-[var(--hc-muted)] hover:text-[var(--hc-ink)]"
              >
                {copied === p.title ? "Copied" : "Copy citation"}
              </button>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-xs text-[var(--hc-muted)]">
        Showing {shown.length} of {publications.length} publications
      </p>
    </>
  );
}
