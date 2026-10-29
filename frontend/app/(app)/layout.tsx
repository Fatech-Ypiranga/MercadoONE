"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { useAuth } from "@/components/auth-provider";
import { CommandPalette } from "@/components/command-palette";
import { NavRail } from "@/components/nav-rail";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p role="status" className="text-sm text-muted-foreground">
          Carregando sessão…
        </p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Pular para o conteúdo
      </a>
      <CommandPalette />
      <div className="flex min-h-screen">
        <div className="sticky top-0 h-screen shrink-0 overflow-y-auto">
          <NavRail />
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <AppHeader />
          <main id="conteudo" tabIndex={-1} className="flex-1 px-4 py-6 outline-none sm:px-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
