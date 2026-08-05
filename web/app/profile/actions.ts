"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { requireLabMember } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

function formString(formData: FormData, key: string) {
  const value = String(formData.get(key) ?? "").trim();
  return value || null;
}

export async function updateProfile(formData: FormData) {
  const { user, authorized } = await requireLabMember();
  if (!user?.email || !authorized) {
    redirect("/login?next=/profile");
  }

  const supabase = await createClient();
  const { error } = await supabase
    .from("lab_members")
    .update({
      display_name: formString(formData, "display_name"),
      google_scholar: formString(formData, "google_scholar"),
      website: formString(formData, "website"),
      github: formString(formData, "github"),
      linkedin: formString(formData, "linkedin"),
    })
    .ilike("email", user.email);

  if (error) {
    throw new Error(error.message);
  }

  revalidatePath("/profile");
  redirect("/profile?saved=1");
}
