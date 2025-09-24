"use client";

import { useEffect } from "react";
import { supabase } from "../lib/supabaseClient";
import { useAuth } from "../app/hooks/useAuth";
import { redirect } from "next/navigation";
import { routes } from "@/utils/routes";
import { useSearchParams } from "next/navigation";

export function HomePage() {
  const search = useSearchParams();
  const { data: user, isLoading } = useAuth();
  useEffect(() => {
    if (!isLoading && user) {
      const redirectTo = search.get("redirect-to");
      if (redirectTo) {
        try {
          redirect(decodeURIComponent(redirectTo));
          return;
        } catch {}
      }
      redirect(routes.master());
    }
  }, [isLoading, user, search]);

  async function signInWithGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { queryParams: { prompt: "select_account" } },
    });
  }

  return (
    <div className="grid min-h-screen place-items-center p-8">
      <div className="w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Welcome</h1>
        <button
          className="w-full px-3 py-2 rounded bg-black text-white"
          onClick={signInWithGoogle}
        >
          Continue with Google
        </button>
      </div>
    </div>
  );
}
