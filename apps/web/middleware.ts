import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

// Only protect /master (and nested paths)
export function middleware(req: NextRequest) {
  const url = req.nextUrl.clone();
  const { pathname } = url;

  // only handle protected routes
  const isProtected = pathname === "/master" || pathname.startsWith("/master/");
  if (!isProtected) return NextResponse.next();

  const hasAuthCookie = req.cookies.has(
    process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME || "auth_token"
  );
  if (!hasAuthCookie) {
    const redirectTo = encodeURIComponent(pathname + url.search);
    url.pathname = "/";
    url.search = `?redirect-to=${redirectTo}`;
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/master", "/master/:path*"],
};
