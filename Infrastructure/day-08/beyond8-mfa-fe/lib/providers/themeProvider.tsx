"use client";

/**
 * Theme context thay cho `next-themes`: không render `<script>` trong cây React
 * (React 19 / Next 16 báo lỗi console). Đồng bộ qua `useSyncExternalStore` + `useEffect` DOM.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

const STORAGE_KEY = "theme";
const THEME_EVENT = "beyond8-theme-change";

export type ThemeName = "light" | "dark" | "system";

export type UseThemeProps = {
  themes: string[];
  forcedTheme?: string | undefined;
  setTheme: (name: string) => void;
  theme?: string | undefined;
  resolvedTheme?: string | undefined;
  systemTheme?: "dark" | "light" | undefined;
};

const emptyTheme: UseThemeProps = {
  themes: [],
  setTheme: () => {},
};

const ThemeContext = createContext<UseThemeProps | null>(null);

function readStoredTheme(): ThemeName {
  if (typeof window === "undefined") return "light";
  try {
    const t = localStorage.getItem(STORAGE_KEY);
    if (t === "light" || t === "dark" || t === "system") return t;
  } catch {
    /* ignore */
  }
  return "light";
}

function getSystemTheme(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Snapshot: khi `system` gắn thêm resolved OS để đổi snapshot khi `prefers-color-scheme` đổi. */
function getThemeSnapshot(): string {
  const stored = readStoredTheme();
  if (stored === "system") return `system:${getSystemTheme()}`;
  return stored;
}

function getThemeServerSnapshot(): string {
  return "light";
}

function subscribeTheme(onStoreChange: () => void) {
  if (typeof window === "undefined") return () => {};

  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY || e.key === null) onStoreChange();
  };
  const onCustom = () => onStoreChange();
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const onMq = () => onStoreChange();

  window.addEventListener("storage", onStorage);
  window.addEventListener(THEME_EVENT, onCustom);
  mq.addEventListener("change", onMq);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(THEME_EVENT, onCustom);
    mq.removeEventListener("change", onMq);
  };
}

function parseStored(raw: string): ThemeName {
  if (raw === "light" || raw === "dark") return raw;
  if (raw.startsWith("system:")) return "system";
  return "light";
}

function parseResolved(raw: string): "light" | "dark" {
  if (raw === "light" || raw === "dark") return raw;
  if (raw.startsWith("system:")) {
    const tail = raw.slice("system:".length);
    return tail === "dark" ? "dark" : "light";
  }
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const raw = useSyncExternalStore(subscribeTheme, getThemeSnapshot, getThemeServerSnapshot);
  const theme = parseStored(raw);
  const resolvedTheme = parseResolved(raw);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(resolvedTheme);
    root.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  const setTheme = useCallback((name: string) => {
    const next = name === "dark" || name === "light" || name === "system" ? name : "light";
    try {
      localStorage.setItem(STORAGE_KEY, next);
      window.dispatchEvent(new Event(THEME_EVENT));
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo((): UseThemeProps => {
    const systemTheme = typeof window !== "undefined" ? getSystemTheme() : undefined;
    return {
      theme,
      setTheme,
      resolvedTheme,
      themes: ["light", "dark", "system"],
      systemTheme,
    };
  }, [theme, setTheme, resolvedTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): UseThemeProps {
  const ctx = useContext(ThemeContext);
  return ctx ?? emptyTheme;
}
