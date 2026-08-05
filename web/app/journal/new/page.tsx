import Link from "next/link";
import { redirect } from "next/navigation";

import { createJournalEntry } from "@/app/journal/actions";
import { JournalEntryForm } from "@/components/journal-entry-form";
import { requireLabMember } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

export default async function NewJournalEntryPage() {
  const { user, authorized } = await requireLabMember();
  if (!user) redirect("/login?next=/journal/new");
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect("/login?next=/journal/new");
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-10 md:px-8">
      <Link
        href="/journal"
        className="text-sm text-muted-foreground hover:text-primary"
      >
        ← Journal
      </Link>
      <h1 className="mt-2 mb-8 font-heading text-4xl font-medium">
        New journal entry
      </h1>
      <JournalEntryForm action={createJournalEntry} submitLabel="Create entry" />
    </div>
  );
}
