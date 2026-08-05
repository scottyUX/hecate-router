"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { createClient } from "@/lib/supabase/client";

/**
 * Handles hash-based auth redirects (invite / recovery) where tokens arrive
 * in the URL fragment instead of ?code=.
 */
function ConfirmClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/journal";
  const [message, setMessage] = useState("Confirming your invite…");

  useEffect(() => {
    const run = async () => {
      const hash = window.location.hash.replace(/^#/, "");
      const params = new URLSearchParams(hash);
      const accessToken = params.get("access_token");
      const refreshToken = params.get("refresh_token");
      const type = params.get("type");

      const supabase = createClient();

      if (accessToken && refreshToken) {
        const { error } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (error) {
          setMessage(error.message);
          return;
        }
        window.history.replaceState(null, "", window.location.pathname);
        // Invites and recovery links should always set a password.
        if (
          !type ||
          type === "invite" ||
          type === "recovery" ||
          type === "signup" ||
          type === "magiclink"
        ) {
          router.replace(`/auth/set-password?next=${encodeURIComponent(next)}`);
        } else {
          router.replace(next);
        }
        return;
      }

      // PKCE flow lands on /auth/callback; this page is a fallback.
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (user) {
        router.replace(`/auth/set-password?next=${encodeURIComponent(next)}`);
        return;
      }

      setMessage("Could not confirm this link. Request a new invite or password reset.");
    };

    void run();
  }, [next, router]);

  return (
    <div className="mx-auto mt-20 max-w-md space-y-3 px-5">
      <Link href="/" className="text-sm text-muted-foreground hover:text-primary">
        ← Hecate Lab
      </Link>
      <p className="text-muted-foreground">{message}</p>
    </div>
  );
}

export default function AuthConfirmPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto mt-20 max-w-md px-5 text-muted-foreground">
          Confirming…
        </div>
      }
    >
      <ConfirmClient />
    </Suspense>
  );
}
