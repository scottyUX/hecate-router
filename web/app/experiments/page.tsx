import Link from "next/link";
import { redirect } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { requireLabMember } from "@/lib/auth";
import { EXPERIMENT_REPORTS } from "@/lib/experiments";
import { createClient } from "@/lib/supabase/server";

export default async function ExperimentsIndexPage() {
  const { user, authorized } = await requireLabMember();
  if (!user) redirect("/login?next=/experiments");
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect("/login?next=/experiments");
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-5 py-10 md:px-8">
      <Link href="/" className="text-sm text-muted-foreground hover:text-primary">
        ← Hecate Lab
      </Link>
      <h1 className="mt-2 font-heading text-4xl font-medium">Experiments</h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
        Static React reports — numbers live in the repo, not the journal
        database. Add a new page under <code>web/app/experiments/</code> for
        the next run. Signed in as {user.email}
      </p>
      <ul className="mt-8 space-y-3">
        {EXPERIMENT_REPORTS.map((report) => (
          <li key={report.href}>
            <Link
              href={report.href}
              className="block rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary/40"
            >
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm text-muted-foreground">{report.date}</p>
                <Badge variant="outline">{report.status}</Badge>
              </div>
              <h2 className="mt-1 font-heading text-2xl font-medium">
                {report.title}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {report.summary}
              </p>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-8 text-sm text-muted-foreground">
        Older database notes stay at{" "}
        <Link href="/journal" className="text-primary hover:underline">
          /journal
        </Link>
        .
      </p>
    </div>
  );
}
