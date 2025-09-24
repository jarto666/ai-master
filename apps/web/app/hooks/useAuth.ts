"use client";

import { useMemo } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";
import {
  useQuery,
  UseQueryOptions,
  useQueryClient,
} from "@tanstack/react-query";

type UserProfile = {
  id: string;
  email: string;
  name?: string | null;
};

type UseAuthOptions = {
  query?: Omit<
    UseQueryOptions<
      UserProfile | null,
      unknown,
      UserProfile | null,
      readonly ["auth", "profile"]
    >,
    "queryKey" | "queryFn"
  >;
};

import { supabase as supabaseSingleton } from "../../lib/supabaseClient";

async function fetchProfile(): Promise<UserProfile | null> {
  const res = await fetch("/api/auth/profile", { credentials: "include" });
  if (res.status === 401) return null;
  if (!res.ok) throw new Error("Failed to fetch profile");
  return (await res.json()) as UserProfile;
}

async function establishSessionIfNeeded(): Promise<void> {
  const { data } = await supabaseSingleton.auth.getSession();
  const token = data.session?.access_token;
  if (!token) return;
  try {
    const resp = await fetch("/api/auth/session", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      credentials: "include",
    });
    if (!resp.ok) {
      // swallow; query will still try to fetch profile and fail
    }
  } catch {
    // ignore
  }
}

export function useAuth(options?: UseAuthOptions) {
  // Memoize a supabase client only for actions we need (logout)
  const supabase = useMemo<SupabaseClient | null>(() => supabaseSingleton, []);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["auth", "profile"] as const,
    queryFn: async () => {
      // Attempt to ensure cookie session is set when user is logged in via Supabase
      await establishSessionIfNeeded();
      return await fetchProfile();
    },
    // Defaults that mirror the example config
    retry: false,
    retryOnMount: false,
    refetchOnWindowFocus: options?.query?.refetchOnWindowFocus ?? false,
    staleTime:
      options?.query?.refetchOnWindowFocus === true
        ? 0
        : options?.query?.staleTime ?? Infinity,
    ...options?.query,
  });

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    await supabase?.auth.signOut();
    // Eagerly mark user as logged out for all subscribers
    queryClient.setQueryData(["auth", "profile"], null);
  };

  return {
    ...query,
    data: query.data, // UserProfile | null
    isAuthenticated: !!query.data,
    logout,
  };
}
