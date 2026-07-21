"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { fetchMe, type MeResponse } from "@/lib/api/auth-api";
import { ApiError } from "@/lib/api/client";
import { listStores, type StoreResponse } from "@/lib/api/stores-api";
import { AUTH_EXPIRED_EVENT, clearToken, getToken, setToken } from "@/lib/auth";
import { STORE_SCOPED_QUERY_ROOTS } from "@/lib/live-query";
import {
  clearActiveStoreId,
  resolveActiveStoreId,
  setActiveStoreId,
} from "@/lib/scope";

type AuthContextValue = {
  user: MeResponse | null;
  loading: boolean;
  stores: StoreResponse[];
  storesLoading: boolean;
  activeStoreId: number | null;
  activeStore: StoreResponse | null;
  setStoreId: (storeId: number) => void;
  loginWithToken: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [stores, setStores] = useState<StoreResponse[]>([]);
  const [storesLoading, setStoresLoading] = useState(false);
  const [activeStoreId, setActiveStoreIdState] = useState<number | null>(null);

  const loadStores = useCallback(async (me: MeResponse) => {
    setStoresLoading(true);
    try {
      const list = await listStores();
      const activeOnly = list.filter((store) => store.is_active);
      setStores(activeOnly);

      const preferred = resolveActiveStoreId(me);
      const validPreferred =
        preferred != null && activeOnly.some((store) => store.id === preferred)
          ? preferred
          : activeOnly[0]?.id ?? null;

      if (validPreferred != null) {
        setActiveStoreId(validPreferred);
        setActiveStoreIdState(validPreferred);
      } else {
        clearActiveStoreId();
        setActiveStoreIdState(null);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        throw error;
      }
      setStores([]);
    } finally {
      setStoresLoading(false);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setStores([]);
      setActiveStoreIdState(null);
      setLoading(false);
      return;
    }

    try {
      const me = await fetchMe();
      setUser(me);
      await loadStores(me);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearToken();
        clearActiveStoreId();
        setUser(null);
        setStores([]);
        setActiveStoreIdState(null);
      } else {
        throw error;
      }
    } finally {
      setLoading(false);
    }
  }, [loadStores]);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    const onExpired = () => {
      clearToken();
      clearActiveStoreId();
      setUser(null);
      setStores([]);
      setActiveStoreIdState(null);
      queryClient.clear();
      router.replace("/login");
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [queryClient, router]);

  const loginWithToken = useCallback(
    async (token: string) => {
      if (token.split(".").length !== 3) {
        throw new Error("Token inválido.");
      }
      setToken(token);
      setLoading(true);
      await refreshUser();
      router.replace("/dashboard");
    },
    [refreshUser, router],
  );

  const logout = useCallback(() => {
    clearToken();
    clearActiveStoreId();
    setUser(null);
    setStores([]);
    setActiveStoreIdState(null);
    queryClient.clear();
    router.replace("/login");
  }, [queryClient, router]);

  const setStoreId = useCallback(
    (storeId: number) => {
      setActiveStoreId(storeId);
      setActiveStoreIdState(storeId);
      for (const root of STORE_SCOPED_QUERY_ROOTS) {
        void queryClient.invalidateQueries({ queryKey: [root] });
      }
    },
    [queryClient],
  );

  const activeStore = useMemo(
    () => stores.find((store) => store.id === activeStoreId) ?? null,
    [stores, activeStoreId],
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      stores,
      storesLoading,
      activeStoreId,
      activeStore,
      setStoreId,
      loginWithToken,
      logout,
      refreshUser,
    }),
    [
      user,
      loading,
      stores,
      storesLoading,
      activeStoreId,
      activeStore,
      setStoreId,
      loginWithToken,
      logout,
      refreshUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider");
  }
  return ctx;
}
