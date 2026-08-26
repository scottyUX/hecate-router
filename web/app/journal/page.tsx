import Link from "next/link";
import { redirect } from "next/navigation";

import { signOut } from "@/app/login/actions";
import { Button, buttonVariants } from "@/components/ui/button";
import { requireLabMember } from "@/lib/auth";
import type { JournalEntry } from "@/lib/journal";
import { createClient } from "@/lib/supabase/server";
import { cn } from "@/lib/utils";

export default async function JournalIndexPage() {
  const { user, authorized } = await requireLabMember();
  if (!user) redirect("/login?next=/journal");
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect("/login?next=/journal");
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("journal_entries")
    .select("*")
    .order("date", { ascending: false });

  if (error) {
    throw new Error(error.message);
  }

  const entries = (data ?? []) as JournalEntry[];

  return (
    <div className="mx-auto w-full max-w-4xl px-5 py-10 md:px-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary">
            ← Hecate Lab
          </Link>
          <h1 className="mt-2 font-heading text-4xl font-medium">Lab journal</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            Database archive. New experiment write-ups are static pages under{" "}
            <Link href="/experiments" className="text-primary hover:underline">
              Experiments
            </Link>
            . Signed in as {user.email}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/experiments"
            className={cn(buttonVariants(), "h-9 px-3")}
          >
            Experiments
          </Link>
          <Link
            href="/journal/new"
            className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}
          >
            New archive entry
          </Link>
          <Link
            href="/profile"
            className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}
          >
            Profile
          </Link>
          <form action={signOut}>
            <Button type="submit" variant="outline">
              Sign out
            </Button>
          </form>
        </div>
      </div>

      {entries.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-muted-foreground">
          No entries yet. Create the first experiment note.
        </div>
      ) : (
        <ul className="space-y-3">
          {entries.map((entry) => (
            <li key={entry.id}>
              <Link
                href={`/journal/${entry.entry_id}`}
                className="block rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary/40"
              >
                <p className="text-sm text-muted-foreground">{entry.date}</p>
                <h2 className="mt-1 font-heading text-2xl font-medium">
                  {entry.title}
                </h2>
                {entry.author_email ? (
                  <p className="mt-2 text-sm text-muted-foreground">
                    {entry.author_email}
                  </p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
