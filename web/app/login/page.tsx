"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "reset">("signin");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/journal";
  const authError = searchParams.get("error");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setIsLoading(true);

    try {
      const supabase = createClient();
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) throw signInError;

      const userEmail = data.user?.email?.toLowerCase();
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
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setIsLoading(true);

    try {
      const supabase = createClient();
      // Always send recovery links to the deployed lab site. Localhost as
      // redirectTo is rejected (or falls back to Site URL) unless it is
      // explicitly allowlisted — and Site URL must not be localhost in prod.
      const PRODUCTION_ORIGIN = "https://hecate-production.up.railway.app";
      const siteOrigin = (
        process.env.NEXT_PUBLIC_SITE_URL ||
        (window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1"
          ? PRODUCTION_ORIGIN
          : window.location.origin)
      ).replace(/\/$/, "");
      const redirectTo = `${siteOrigin}/auth/callback?type=recovery&next=${encodeURIComponent(next)}`;
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(
        email,
        { redirectTo }
      );
      if (resetError) throw resetError;
      setInfo("Check your email for a password reset link.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send reset email");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form
      onSubmit={mode === "signin" ? handleLogin : handleReset}
      className="mx-auto mt-20 w-full max-w-md space-y-5 px-5"
    >
      <div className="space-y-2">
        <Link href="/" className="text-sm text-muted-foreground hover:text-primary">
          ← Hecate Lab
        </Link>
        <h1 className="font-heading text-3xl font-medium">
          {mode === "signin" ? "Lab sign in" : "Reset password"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {mode === "signin"
            ? "Journal access is invite-only for lab members."
            : "We’ll email you a link to set a new password."}
        </p>
      </div>

      {(authError || error) && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error ||
            (searchParams.get("error_code") === "otp_expired" ||
            searchParams.get("error_description")?.includes("expired")
              ? "That password reset link is invalid or has expired. Use “Forgot password?” below to request a new one, then open the email on this same device/browser."
              : authError === "auth_callback_error"
                ? "That invite or reset link is invalid or expired. Request a new one."
                : authError)}
        </div>
      )}

      {info ? (
        <div className="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-foreground">
          {info}
        </div>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </div>

      {mode === "signin" ? (
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
      ) : null}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading
          ? mode === "signin"
            ? "Signing in…"
            : "Sending…"
          : mode === "signin"
            ? "Sign in"
            : "Send reset link"}
      </Button>

      <button
        type="button"
        className="w-full text-center text-sm text-muted-foreground transition-colors hover:text-primary"
        onClick={() => {
          setMode(mode === "signin" ? "reset" : "signin");
          setError(null);
          setInfo(null);
        }}
      >
        {mode === "signin" ? "Forgot password?" : "Back to sign in"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto mt-20 max-w-md px-5 text-muted-foreground">
          Loading…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
