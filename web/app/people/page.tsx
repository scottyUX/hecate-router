import type { Metadata } from "next";
import Image from "next/image";
import { ArrowUpRight } from "lucide-react";

import { PageIntro, SiteShell } from "@/components/site-shell";
import { PEOPLE, type Person } from "@/lib/lab";

export const metadata: Metadata = {
  title: "People · Hecate Lab",
  description: "Faculty and students in Hecate Lab at UC Santa Cruz.",
};

function initials(name: string) {
  const parts = name.replace(/\./g, "").split(/\s+/).filter(Boolean);
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function PersonCard({ person, compact = false }: { person: Person; compact?: boolean }) {
  return (
    <article className={`flex flex-col ${compact ? "border-t-2 border-[var(--hc-ink)] pt-2" : ""}`}>
      <div
        className={`relative aspect-square w-full overflow-hidden rounded-sm bg-[#e6e3dc] ${
          compact ? "hidden" : ""
        }`}
      >
        {person.photo ? (
          <Image
            src={person.photo}
            alt={person.name}
            fill
            sizes="(min-width: 1024px) 260px, (min-width: 640px) 45vw, 90vw"
            className="object-cover"
            style={person.photoPosition ? { objectPosition: person.photoPosition } : undefined}
          />
        ) : (
          <div
            className="flex h-full items-center justify-center text-6xl font-bold tracking-[-0.04em] text-[var(--hc-ink)]/80"
            aria-hidden="true"
          >
            {initials(person.name)}
          </div>
        )}
      </div>
      <h3
        className={`text-lg font-bold tracking-[-0.02em] text-[var(--hc-ink)] ${
          compact ? "mt-1" : "mt-4"
        }`}
      >
        {person.name}
      </h3>
      <p className="text-sm text-[var(--hc-body)]">{person.role}</p>
      {person.affiliation ? (
        <p className="text-xs text-[var(--hc-muted)]">{person.affiliation}</p>
      ) : null}
      {person.blurb ? (
        <p className="mt-3 text-sm leading-relaxed text-[var(--hc-body)]">{person.blurb}</p>
      ) : null}
      {person.linkedin || person.website ? (
        <p className="mt-3 flex gap-4 text-sm font-semibold">
          {person.linkedin ? (
            <a
              href={person.linkedin}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-0.5 text-[var(--hc-ink)] underline-offset-4 hover:underline"
            >
              LinkedIn <ArrowUpRight className="size-3.5" aria-hidden="true" />
            </a>
          ) : null}
          {person.website ? (
            <a
              href={person.website}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-0.5 text-[var(--hc-ink)] underline-offset-4 hover:underline"
            >
              Website <ArrowUpRight className="size-3.5" aria-hidden="true" />
            </a>
          ) : null}
        </p>
      ) : null}
    </article>
  );
}

export default function PeoplePage() {
  return (
    <SiteShell current="/people">
      <section className="px-5 pt-16 pb-24 md:px-8 md:pt-24">
        <div className="mx-auto w-full max-w-[1120px]">
          <PageIntro title="People">
            Faculty and students at UC Santa Cruz working on cost-aware routing
            and advising for AI coding agents.
          </PageIntro>

          {PEOPLE.map((group) => (
            <div key={group.title} className="mt-14">
              <h2 className="border-b border-[var(--hc-rule)] pb-3 text-xl font-bold tracking-[-0.02em] text-[var(--hc-ink)]">
                {group.title}
              </h2>
              <div
                className={`mt-8 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-4 ${
                  group.compact ? "gap-y-8" : "gap-y-12"
                }`}
              >
                {group.people.map((person) => (
                  <PersonCard key={person.slug} person={person} compact={group.compact} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </SiteShell>
  );
}
