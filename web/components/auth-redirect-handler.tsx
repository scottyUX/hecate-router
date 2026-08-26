"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Supabase recovery/invite emails sometimes land on Site URL (`/`) with either:
 * - error query/hash params (expired OTP, access_denied), or
 * - hash tokens (implicit flow) that `/auth/confirm` knows how to finish.
 *
 * Catch those on the homepage so users are not stuck on a blank marketing page.
 */
export function AuthRedirectHandler() {
  const router = useRouter();

  useEffect(() => {
    const search = new URLSearchParams(window.location.search);
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));

    const error =
      search.get("error") ||
      hash.get("error") ||
      search.get("error_code") ||
      hash.get("error_code");

    if (error) {
      const code = search.get("error_code") || hash.get("error_code") || "";
      const desc =
        search.get("error_description") || hash.get("error_description") || "";
      const params = new URLSearchParams({ error: "auth_callback_error" });
      if (code) params.set("error_code", code);
      if (desc) params.set("error_description", desc);
      router.replace(`/login?${params.toString()}`);
      return;
    }

    const accessToken = hash.get("access_token");
    const refreshToken = hash.get("refresh_token");
    if (accessToken && refreshToken) {
      window.location.replace(`/auth/confirm${window.location.hash}`);
    }
  }, [router]);

  return null;
}
