import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";

export async function getSessionUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
}

export async function isLabMember(email: string | undefined | null) {
  if (!email) return false;
  const supabase = await createClient();
  const normalized = email.toLowerCase();
  const { data } = await supabase
    .from("lab_members")
    .select("email")
    .ilike("email", normalized)
    .maybeSingle();
  return Boolean(data);
}

export async function requireLabMember() {
  const user = await getSessionUser();
  if (!user?.email) return { user: null, authorized: false as const };
  const authorized = await isLabMember(user.email);
  return { user, authorized };
}

export async function requireJournalPage(nextPath: string) {
  const { user, authorized } = await requireLabMember();
  if (!user) redirect(`/login?next=${nextPath}`);
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect(`/login?next=${nextPath}`);
  }
  return user;
}
