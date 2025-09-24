import type { ReactNode } from "react";
import { AuthWrapper } from "./AuthWrapper";

export default function ProtectedLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return <AuthWrapper>{children}</AuthWrapper>;
}
