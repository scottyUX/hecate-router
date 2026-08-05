"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";

function SetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/journal";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const load = async () => {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user?.email) {
        router.replace(`/login?next=${encodeURIComponent(next)}`);
        return;
      }
      setEmail(user.email);
      setReady(true);
    };
    void load();
  }, [next, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const supabase = createClient();
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      });
      if (updateError) throw updateError;

      const {
        data: { user },
      } = await supabase.auth.getUser();
      const userEmail = user?.email?.toLowerCase();
      if (!userEmail) throw new Error("No email on account.");

      const { data: member } = await supabase
        .from("lab_members")
        .select("email")
        .ilike("email", userEmail)
        .maybeSingle();

      if (!member) {
        await supabase.auth.signOut();
        throw new Error(
          "This account is not on the lab member allowlist. Ask a lab admin to add your email."
        );
      }

      router.push(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not set password");
    } finally {
      setIsLoading(false);
    }
  };

  if (!ready) {
    return (
      <div className="mx-auto mt-20 max-w-md px-5 text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto mt-20 w-full max-w-md space-y-5 px-5"
    >
      <div className="space-y-2">
        <Link href="/" className="text-sm text-muted-foreground hover:text-primary">
          ← Hecate Lab
        </Link>
        <h1 className="font-heading text-3xl font-medium">Set your password</h1>
        <p className="text-sm text-muted-foreground">
          Choose a password for {email} so you can sign in to the lab journal.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">New password</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          autoComplete="new-password"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirm">Confirm password</Label>
        <Input
          id="confirm"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          minLength={6}
          autoComplete="new-password"
        />
      </div>

      {error ? (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? "Saving…" : "Save password and continue"}
      </Button>
    </form>
  );
}

export default function SetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto mt-20 max-w-md px-5 text-muted-foreground">
          Loading…
        </div>
      }
    >
      <SetPasswordForm />
    </Suspense>
  );
}
