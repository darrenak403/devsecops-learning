interface CookieOptions {
  maxAge?: number;
  path?: string;
  secure?: boolean;
  sameSite?: "strict" | "lax" | "none";
  httpOnly?: boolean;
  domain?: string;
}

function getCookieDomain(): string | undefined {
  const isProduction =
    process.env.NODE_ENV === "production" || process.env.NEXT_PUBLIC_ENV === "production";

  if (!isProduction) return undefined;
  const configuredDomain = process.env.NEXT_PUBLIC_COOKIE_DOMAIN || undefined;
  if (!configuredDomain) return undefined;

  // Local development must not force production cookie domain.
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    if (hostname === "localhost" || hostname === "127.0.0.1") return undefined;
    if (!hostname.endsWith(configuredDomain.replace(/^\./, ""))) return undefined;
  }

  return configuredDomain;
}

export function getSecureCookieConfig(customOptions: Partial<CookieOptions> = {}): CookieOptions {
  const isProduction =
    process.env.NODE_ENV === "production" || process.env.NEXT_PUBLIC_ENV === "production";
  const isSecureEnvironment =
    typeof window !== "undefined" ? window.location.protocol === "https:" : isProduction;

  const defaultConfig: CookieOptions = {
    maxAge: 60 * 60 * 24 * 7,
    path: "/",
    sameSite: "strict",
    secure: isSecureEnvironment,
    domain: getCookieDomain()
  };

  return { ...defaultConfig, ...customOptions };
}

export function getAuthCookieConfig(rememberMe = false): CookieOptions {
  return getSecureCookieConfig({
    maxAge: rememberMe ? 60 * 60 * 24 * 30 : 60 * 60 * 24 * 7
  });
}
