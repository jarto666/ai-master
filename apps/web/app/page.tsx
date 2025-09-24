import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { HomePage } from "../components/HomePage";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const cookieJar = await cookies();
  const cookieName = process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME || "auth_token";
  const authCookie = cookieJar.get(cookieName);
  const resolved = await searchParams;
  const redirectTo = resolved?.["redirect-to"] as string | undefined;

  if (authCookie) {
    if (redirectTo) {
      try {
        return redirect(decodeURIComponent(redirectTo));
      } catch {}
    }
    return redirect("/master");
  }

  return <HomePage />;
}
