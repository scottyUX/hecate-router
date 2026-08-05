import Link from "next/link";
import { redirect } from "next/navigation";

import { updateProfile } from "@/app/profile/actions";
import { signOut } from "@/app/login/actions";
import { ChangePasswordForm } from "@/components/change-password-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { requireLabMember } from "@/lib/auth";
import type { LabMemberProfile } from "@/lib/profile";
import { createClient } from "@/lib/supabase/server";

type Props = {
  searchParams: Promise<{ saved?: string }>;
};

export default async function ProfilePage({ searchParams }: Props) {
  const { saved } = await searchParams;
  const { user, authorized } = await requireLabMember();
  if (!user?.email) redirect("/login?next=/profile");
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect("/login?next=/profile");
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("lab_members")
    .select(
      "email, display_name, google_scholar, website, github, linkedin, created_at"
    )
    .ilike("email", user.email)
    .maybeSingle();

  if (error) throw new Error(error.message);
  if (!data) redirect("/login?next=/profile");

  const profile = data as LabMemberProfile;

  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-10 md:px-8">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/journal"
            className="text-sm text-muted-foreground hover:text-primary"
          >
            ← Journal
          </Link>
          <h1 className="mt-2 font-heading text-4xl font-medium">Profile</h1>
          <p className="mt-1 text-sm text-muted-foreground">{profile.email}</p>
        </div>
        <form action={signOut}>
          <Button type="submit" variant="outline">
            Sign out
          </Button>
        </form>
      </div>

      {saved ? (
        <div className="mb-6 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm">
          Profile saved.
        </div>
      ) : null}

      <section className="space-y-4 rounded-2xl border border-border bg-card p-6">
        <h2 className="font-heading text-2xl font-medium">Public links</h2>
        <p className="text-sm text-muted-foreground">
          Name and links for your lab presence. Leave blank to hide a field.
        </p>
        <form action={updateProfile} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="display_name">Name</Label>
            <Input
              id="display_name"
              name="display_name"
              defaultValue={profile.display_name ?? ""}
              placeholder="Your name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="website">Personal website</Label>
            <Input
              id="website"
              name="website"
              type="url"
              defaultValue={profile.website ?? ""}
              placeholder="https://…"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="google_scholar">Google Scholar</Label>
            <Input
              id="google_scholar"
              name="google_scholar"
              type="url"
              defaultValue={profile.google_scholar ?? ""}
              placeholder="https://scholar.google.com/…"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="github">GitHub</Label>
            <Input
              id="github"
              name="github"
              type="url"
              defaultValue={profile.github ?? ""}
              placeholder="https://github.com/…"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="linkedin">LinkedIn</Label>
            <Input
              id="linkedin"
              name="linkedin"
              type="url"
              defaultValue={profile.linkedin ?? ""}
              placeholder="https://linkedin.com/in/…"
            />
          </div>
          <Button type="submit">Save profile</Button>
        </form>
      </section>

      <Separator className="my-10" />

      <section className="space-y-4 rounded-2xl border border-border bg-card p-6">
        <h2 className="font-heading text-2xl font-medium">Change password</h2>
        <p className="text-sm text-muted-foreground">
          Update the password you use to sign in to the lab journal.
        </p>
        <ChangePasswordForm />
      </section>
    </div>
  );
}
