"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "@/lib/api";
import type { MeResponse } from "@/lib/types";

interface AuthState {
  ready: boolean;
  me: MeResponse | null;
  login: (name: string) => Promise<MeResponse>;
  logout: () => Promise<void>;
  refresh: () => Promise<MeResponse | null>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<MeResponse | null>(null);

  const clear = useCallback(() => {
    setToken(null);
    setMe(null);
    qc.clear();
  }, [qc]);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      return null;
    }
    try {
      const m = await api.me();
      setMe(m);
      return m;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clear();
      router.replace("/login");
    });
    let cancelled = false;
    (async () => {
      let m: MeResponse | null = null;
      if (getToken()) {
        try {
          m = await api.me();
        } catch {
          m = null;
        }
      } else {
        await Promise.resolve();
      }
      if (!cancelled) {
        setMe(m);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
      setUnauthorizedHandler(null);
    };
  }, [clear, router]);

  const login = useCallback(async (name: string) => {
    const res = await api.login(name);
    setToken(res.token);
    const m = await api.me();
    setMe(m);
    return m;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      clear();
      router.replace("/login");
    }
  }, [clear, router]);

  const value = useMemo(
    () => ({ ready, me, login, logout, refresh }),
    [ready, me, login, logout, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Where a signed-in user should land. */
export function homePath(me: MeResponse): string {
  if (!me.has_cv) return "/onboarding";
  return me.latest_search_id ? `/search/${me.latest_search_id}` : "/new-search";
}
