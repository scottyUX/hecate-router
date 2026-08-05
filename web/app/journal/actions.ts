"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { requireLabMember } from "@/lib/auth";
import {
  makeEntryId,
  parseCsvList,
  type JournalEntryInput,
  type JournalStatus,
  type JournalVisibility,
} from "@/lib/journal";
import { createClient } from "@/lib/supabase/server";

function formString(formData: FormData, key: string) {
  return String(formData.get(key) ?? "").trim();
}

function readEntryInput(formData: FormData): JournalEntryInput {
  const title = formString(formData, "title");
  const date = formString(formData, "date") || new Date().toISOString().slice(0, 10);
  const entryIdRaw = formString(formData, "entry_id");
  const entry_id = entryIdRaw || makeEntryId(date, title);

  return {
    entry_id,
    title,
    date,
    visibility: formString(formData, "visibility") as JournalVisibility,
    status: formString(formData, "status") as JournalStatus,
    component: formData.getAll("component").map(String),
    commit: formString(formData, "commit"),
    related_entries: parseCsvList(formString(formData, "related_entries")),
    tags: parseCsvList(formString(formData, "tags")),
    context: formString(formData, "context"),
    method: formString(formData, "method"),
    result: formString(formData, "result"),
    interpretation: formString(formData, "interpretation"),
    next_steps: formString(formData, "next_steps"),
    notes: formString(formData, "notes"),
  };
}

export async function createJournalEntry(formData: FormData) {
  const { user, authorized } = await requireLabMember();
  if (!user || !authorized) redirect("/login?next=/journal/new");

  const input = readEntryInput(formData);
  if (!input.title) {
    throw new Error("Title is required");
  }

  const supabase = await createClient();
  const { error } = await supabase.from("journal_entries").insert({
    ...input,
    commit: input.commit || null,
    author_id: user.id,
    author_email: user.email ?? null,
  });

  if (error) {
    throw new Error(error.message);
  }

  revalidatePath("/journal");
  redirect(`/journal/${input.entry_id}`);
}

export async function updateJournalEntry(entryId: string, formData: FormData) {
  const { user, authorized } = await requireLabMember();
  if (!user || !authorized) redirect(`/login?next=/journal/${entryId}/edit`);

  const input = readEntryInput(formData);
  if (!input.title) {
    throw new Error("Title is required");
  }

  const supabase = await createClient();
  const { error } = await supabase
    .from("journal_entries")
    .update({
      ...input,
      commit: input.commit || null,
    })
    .eq("entry_id", entryId);

  if (error) {
    throw new Error(error.message);
  }

  revalidatePath("/journal");
  revalidatePath(`/journal/${input.entry_id}`);
  redirect(`/journal/${input.entry_id}`);
}

export async function deleteJournalEntry(entryId: string) {
  const { user, authorized } = await requireLabMember();
  if (!user || !authorized) redirect("/login?next=/journal");

  const supabase = await createClient();
  const { error } = await supabase
    .from("journal_entries")
    .delete()
    .eq("entry_id", entryId);

  if (error) {
    throw new Error(error.message);
  }

  revalidatePath("/journal");
  redirect("/journal");
}
