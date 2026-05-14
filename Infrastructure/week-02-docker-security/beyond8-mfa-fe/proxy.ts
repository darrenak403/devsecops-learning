import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtDecode } from "jwt-decode";
import { ROLE_ADMIN, getPrimaryRole } from "@/lib/types/roles";
import { getAuthCookieConfig } from "@/utils/cookieConfig";

const getUserRoles = (token: string | undefined): string[] => {
  if (!token) return [];

  try {
    const decoded = jwtDecode(token) as { role?: string | string[]; exp?: number } | null;
    if (!decoded?.role) return [];
    return Array.isArray(decoded.role) ? decoded.role : [decoded.role];
  } catch {
    return [];
  }
};

const isTokenExpired = (token: string | undefined): boolean => {
  if (!token) return true;

  try {
    const decoded = jwtDecode(token) as { exp?: number } | null;
    if (!decoded?.exp) return true;
    return decoded.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
};

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("auth_token")?.value;
  const tokenExpired = isTokenExpired(token);
  const userRoles = getUserRoles(token);
  const primaryRole = getPrimaryRole(userRoles);

  const publicRoutes = ["/login"];
  const isPublic = publicRoutes.includes(pathname);

  if ((!token || tokenExpired) && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token && !tokenExpired && pathname === "/login") {
    if (primaryRole === ROLE_ADMIN) {
      return NextResponse.redirect(new URL("/admin", request.url));
    }

    const response = NextResponse.next();
    const cookieConfig = getAuthCookieConfig();
    response.cookies.delete({ name: "auth_token", domain: cookieConfig.domain, path: cookieConfig.path });
    return response;
  }

  if (token && !tokenExpired && primaryRole !== ROLE_ADMIN) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    const cookieConfig = getAuthCookieConfig();
    response.cookies.delete({ name: "auth_token", domain: cookieConfig.domain, path: cookieConfig.path });
    return response;
  }

  if (pathname === "/") {
    return NextResponse.redirect(new URL("/admin", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/admin/:path*", "/dashboard/:path*"],
};
