"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { Provider } from "react-redux";
import { PersistGate } from "redux-persist/integration/react";
import { QueryProvider } from "./queryProvider";
import { ThemeProvider } from "./themeProvider";
import { useAuthSyncAcrossTabs } from "@/hooks/useAuthSyncAcrossTabs";
import { configureApiAuthBridge, apiService } from "@/lib/api/core";
import { logout, setTokens } from "@/lib/redux/authSlice";
import { persistor, store } from "@/lib/redux/store";

configureApiAuthBridge({
  getRefreshToken: () => store.getState().auth.refreshToken,
  onRefreshSuccess: ({ token, refreshToken }) => {
    store.dispatch(setTokens({ token, refreshToken }));
  },
  onAuthFailure: () => {
    store.dispatch(logout());
  },
});

function AuthSyncProvider({ children }: { children: ReactNode }) {
  useAuthSyncAcrossTabs();

  useEffect(() => {
    const unsubscribe = store.subscribe(() => {
      const token = store.getState().auth.token;
      apiService.setAuthToken(token);
    });

    apiService.setAuthToken(store.getState().auth.token);
    return unsubscribe;
  }, []);

  return <>{children}</>;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <Provider store={store}>
      <PersistGate
        persistor={persistor}
        loading={
          <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-background px-4 text-center">
            <div
              className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-primary"
              aria-hidden
            />
            <p className="text-sm text-muted-foreground">Đang khôi phục phiên đăng nhập…</p>
          </div>
        }
      >
        <QueryProvider>
          <ThemeProvider>
            <AuthSyncProvider>{children}</AuthSyncProvider>
          </ThemeProvider>
        </QueryProvider>
      </PersistGate>
    </Provider>
  );
}
