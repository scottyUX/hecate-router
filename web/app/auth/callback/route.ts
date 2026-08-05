import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/journal";
  const type = searchParams.get("type");

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      // Invite / recovery emails should land on set-password.
      // Pass ?type=invite (or recovery) on the redirect URL when inviting.
      const needsPassword =
        !type ||
        type === "invite" ||
        type === "recovery" ||
        type === "signup" ||
        searchParams.get("set_password") === "1";

      if (needsPassword) {
        const url = new URL("/auth/set-password", origin);
        url.searchParams.set("next", next);
        return NextResponse.redirect(url);
      }

      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  const loginUrl = new URL("/login", origin);
  loginUrl.searchParams.set("error", "auth_callback_error");
  return NextResponse.redirect(loginUrl);
}
