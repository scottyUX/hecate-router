import type { Metadata } from "next";

import { PublicationsList } from "@/components/publications-list";
import { PageIntro, SiteShell } from "@/components/site-shell";
import { PUBLICATIONS } from "@/lib/lab";

export const metadata: Metadata = {
  title: "Publications · Hecate Lab",
  description: "Peer-reviewed papers from Hecate Lab at UC Santa Cruz.",
};

export default function PublicationsPage() {
  return (
    <SiteShell current="/publications">
      <section className="px-5 pt-16 pb-24 md:px-8 md:pt-24">
        <div className="mx-auto w-full max-w-[1120px]">
          <PageIntro title="Publications">
            Published and submitted work from the lab on AI coding agents,
            software metrics and AI in software-engineering education.
          </PageIntro>
          <PublicationsList publications={PUBLICATIONS} />
        </div>
      </section>
    </SiteShell>
  );
}
