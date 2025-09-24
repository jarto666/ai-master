"use client";

import { PropsWithChildren, useLayoutEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../hooks/useAuth";

export function AuthWrapper({ children }: PropsWithChildren) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoading, isAuthenticated, error } = useAuth();

  // If not authorized, redirect to public home
  useLayoutEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center text-sm">
        Auth error. Please refresh the page.
      </div>
    );
  }

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center text-sm">
        Loading...
      </div>
    );
  }

  return children;
}
