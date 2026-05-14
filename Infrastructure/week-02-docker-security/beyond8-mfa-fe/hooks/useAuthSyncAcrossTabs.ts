"use client";

import { useEffect } from "react";
import { useAppDispatch } from "@/lib/redux/hooks";
import { logout } from "@/lib/redux/authSlice";

export function useAuthSyncAcrossTabs() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    const handleLogout = () => dispatch(logout());
    window.addEventListener("logout", handleLogout);

    return () => window.removeEventListener("logout", handleLogout);
  }, [dispatch]);
}
