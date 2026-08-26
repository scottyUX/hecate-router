import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { DeleteEntryButton } from "@/components/delete-entry-button";
import { JournalBody } from "@/components/journal-body";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { requireLabMember } from "@/lib/auth";
import type { JournalEntry } from "@/lib/journal";
import { createClient } from "@/lib/supabase/server";
import { cn } from "@/lib/utils";

type Props = { params: Promise<{ entry_id: string }> };

export default async function JournalEntryPage({ params }: Props) {
  const { entry_id } = await params;
  const { user, authorized } = await requireLabMember();
  if (!user) redirect(`/login?next=/journal/${entry_id}`);
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect(`/login?next=/journal/${entry_id}`);
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("journal_entries")
    .select("*")
    .eq("entry_id", entry_id)
    .maybeSingle();

  if (error) throw new Error(error.message);
  if (!data) notFound();

  const entry = data as JournalEntry;

  const sections = [
    ["Context", entry.context],
    ["Method / What I did", entry.method],
    ["Result", entry.result],
    ["Interpretation", entry.interpretation],
    ["Next", entry.next_steps],
    ["Notes", entry.notes],
  ] as const;

  return (
    <article className="mx-auto w-full max-w-3xl px-5 py-10 md:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/journal"
          className="text-sm text-muted-foreground hover:text-primary"
        >
          ← Journal
        </Link>
        <div className="flex gap-2">
          <Link
            href={`/journal/${entry.entry_id}/edit`}
            className={cn(buttonVariants({ variant: "outline" }), "h-8 px-3")}
          >
            Edit
          </Link>
          <DeleteEntryButton entryId={entry.entry_id} />
        </div>
      </div>

      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{entry.status}</Badge>
          <Badge variant="outline">{entry.visibility}</Badge>
        </div>
        <h1 className="font-heading text-4xl font-medium">{entry.title}</h1>
        <p className="text-sm text-muted-foreground">
          {entry.date} · <code>{entry.entry_id}</code>
          {entry.commit ? (
            <>
              {" "}
              · commit <code>{entry.commit}</code>
            </>
          ) : null}
        </p>
        {entry.component.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {entry.component.map((component) => (
              <Badge key={component} variant="secondary">
                {component}
              </Badge>
            ))}
          </div>
        ) : null}
        {entry.tags.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            Tags: {entry.tags.join(", ")}
          </p>
        ) : null}
        {entry.related_entries.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            Related:{" "}
            {entry.related_entries.map((related, index) => (
              <span key={related}>
                {index > 0 ? ", " : null}
                <Link
                  href={`/journal/${related}`}
                  className="text-primary hover:underline"
                >
                  {related}
                </Link>
              </span>
            ))}
          </p>
        ) : null}
      </header>

      <Separator className="my-8" />

      <div className="space-y-8">
        {sections.map(([title, body]) => (
          <section key={title}>
            <h2 className="mb-2 font-heading text-2xl font-medium">{title}</h2>
            <JournalBody text={body} />
          </section>
        ))}
      </div>
    </article>
  );
}
