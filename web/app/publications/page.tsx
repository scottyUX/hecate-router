import type { Metadata } from "next";

import { PublicationsList } from "@/components/publications-list";
import { PageIntro, SiteShell } from "@/components/site-shell";
import { PUBLICATIONS } from "@/lib/lab";

export const metadata: Metadata = {
  title: "Publications · Hecate Lab",
  description: "Papers from Hecate Lab at UC Santa Cruz.",
};

export default function PublicationsPage() {
  return (
    <SiteShell current="/publications">
      <section className="px-5 pt-16 pb-24 md:px-8 md:pt-24">
        <div className="mx-auto w-full max-w-[1120px]">
          <PageIntro title="Publications">
            Peer-reviewed and forthcoming work on cost-aware routing and
            advising for AI coding agents.
          </PageIntro>
          <PublicationsList publications={PUBLICATIONS} />
        </div>
      </section>
    </SiteShell>
  );
}
