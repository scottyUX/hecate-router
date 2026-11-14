import type { Metadata } from "next";
import Image from "next/image";

import { PageIntro, SiteShell } from "@/components/site-shell";
import { EVENTS } from "@/lib/lab";

export const metadata: Metadata = {
  title: "Events · Hecate Lab",
  description: "Talks and events from Hecate Lab at UC Santa Cruz.",
};

export default function EventsPage() {
  const events = [...EVENTS].sort((a, b) => b.sortDate.localeCompare(a.sortDate));
  return (
    <SiteShell current="/events">
      <section className="px-5 pt-16 pb-24 md:px-8 md:pt-24">
        <div className="mx-auto w-full max-w-[1120px]">
          <PageIntro title="Events">Talks, summits and workshops where the lab has presented.</PageIntro>

          <ol className="mt-4">
            {events.map((event) => (
              <li
                key={event.title + event.sortDate}
                className="grid gap-4 border-b border-[var(--hc-rule)] py-8 md:grid-cols-[10rem_1fr_20rem] md:gap-8"
              >
                <p className="font-mono text-xs tracking-[0.08em] text-[var(--hc-muted)] uppercase md:pt-1.5">
                  {event.date}
                </p>
                <div>
                  <h2 className="text-2xl font-bold tracking-[-0.03em] text-[var(--hc-ink)]">
                    {event.title}
                  </h2>
                  {event.place ? (
                    <p className="mt-1 text-sm text-[var(--hc-muted)]">{event.place}</p>
                  ) : null}
                  <p className="mt-3 max-w-2xl text-base leading-relaxed text-[var(--hc-body)]">
                    {event.detail}
                  </p>
                </div>
                {event.image ? (
                  <div className="relative aspect-[4/3] w-full overflow-hidden rounded-sm bg-[#e6e3dc]">
                    <Image
                      src={event.image.src}
                      alt={event.image.alt}
                      fill
                      sizes="(min-width: 768px) 320px, 90vw"
                      className="object-cover"
                      style={{ objectPosition: event.image.position ?? "50% 50%" }}
                    />
                  </div>
                ) : null}
              </li>
            ))}
          </ol>
        </div>
      </section>
    </SiteShell>
  );
}
