import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { updateJournalEntry } from "@/app/journal/actions";
import { DeleteEntryButton } from "@/components/delete-entry-button";
import { JournalEntryForm } from "@/components/journal-entry-form";
import { requireLabMember } from "@/lib/auth";
import type { JournalEntry } from "@/lib/journal";
import { createClient } from "@/lib/supabase/server";

type Props = { params: Promise<{ entry_id: string }> };

export default async function EditJournalEntryPage({ params }: Props) {
  const { entry_id } = await params;
  const { user, authorized } = await requireLabMember();
  if (!user) redirect(`/login?next=/journal/${entry_id}/edit`);
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect(`/login?next=/journal/${entry_id}/edit`);
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
  const updateAction = updateJournalEntry.bind(null, entry.entry_id);

  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-10 md:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/journal/${entry.entry_id}`}
          className="text-sm text-muted-foreground hover:text-primary"
        >
          ← Back to entry
        </Link>
        <DeleteEntryButton entryId={entry.entry_id} />
      </div>
      <h1 className="mb-8 font-heading text-4xl font-medium">Edit entry</h1>
      <JournalEntryForm
        action={updateAction}
        initial={entry}
        submitLabel="Save changes"
      />
    </div>
  );
}
