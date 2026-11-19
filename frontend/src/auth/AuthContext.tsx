import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError, api, setUnauthorizedHandler } from "../api/client";
import type { Me } from "../api/types";
import { SYSTEM, TZ_STORAGE_KEY, resolveZone } from "../lib/time";

interface AuthState {
  me: Me | null;
  loading: boolean;
  /** The session couldn't be checked because the server is unreachable (not "signed out"). */
  unreachable: boolean;
  retry: () => void;
  /** The viewer's stored preference: "system" or an IANA zone from the allow-list. */
  tzPreference: string;
  /** The zone actually used for formatting. */
  zone: string;
  can: (permission: string) => boolean;
  signIn: (username: string, password: string) => Promise<Me>;
  signOut: () => Promise<void>;
  setTimezone: (value: string) => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Forget everything fetched for the previous user, but keep the ["me"] query itself: the
 * provider is subscribed to it, and clearing it would orphan that subscription.
 */
function dropUserData(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" && q.queryKey[0] !== "timezones" });
}

function storedTz(): string {
  try {
    return localStorage.getItem(TZ_STORAGE_KEY) || SYSTEM;
  } catch {
    return SYSTEM;
  }
}

function rememberTz(value: string): void {
  try {
    localStorage.setItem(TZ_STORAGE_KEY, value);
  } catch {
    /* storage blocked */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [anonTz, setAnonTz] = useState(storedTz);

  const meQuery = useQuery<Me | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api.get<Me>("/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const me = meQuery.data ?? null;

  useEffect(() => {
    // Any 401 from any request means the session ended: drop cached data and show login.
    setUnauthorizedHandler(() => {
      dropUserData(queryClient);
      queryClient.setQueryData(["me"], null);
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  const signIn = useCallback(
    async (username: string, password: string) => {
      const user = await api.post<Me>("/auth/login", { username, password });
      dropUserData(queryClient);
      queryClient.setQueryData(["me"], user);
      // A choice made before signing in is carried into the account once.
      const local = storedTz();
      if (local !== SYSTEM && user.display_timezone === SYSTEM) {
        try {
          const updated = await api.patch<Me>("/me/preferences", { display_timezone: local });
          queryClient.setQueryData(["me"], updated);
          return updated;
        } catch {
          /* keep the server value */
        }
      }
      rememberTz(user.display_timezone);
      return user;
    },
    [queryClient],
  );

  const signOut = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      dropUserData(queryClient);
      queryClient.setQueryData(["me"], null);
    }
  }, [queryClient]);

  const setTimezone = useCallback(
    async (value: string) => {
      rememberTz(value);
      setAnonTz(value);
      if (me) {
        const updated = await api.patch<Me>("/me/preferences", { display_timezone: value });
        queryClient.setQueryData(["me"], updated);
      }
    },
    [me, queryClient],
  );

  const value = useMemo<AuthState>(() => {
    const tzPreference = me?.display_timezone ?? anonTz;
    const permissions = new Set(me?.permissions ?? []);
    return {
      me,
      loading: meQuery.isLoading,
      unreachable: !me && meQuery.error instanceof ApiError && meQuery.error.status === 0,
      retry: () => void meQuery.refetch(),
      tzPreference,
      zone: resolveZone(tzPreference),
      can: (p) => permissions.has(p),
      signIn,
      signOut,
      setTimezone,
    };
  }, [me, anonTz, meQuery.isLoading, meQuery.error, meQuery.refetch, signIn, signOut, setTimezone]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** For screens that only render when signed in (inside RequireAuth). */
export function useMe(): Me {
  const { me } = useAuth();
  if (!me) throw new Error("useMe used outside a signed-in route");
  return me;
}
