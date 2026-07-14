"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { AppSidebar } from "@/components/app-sidebar";
import { useAuth } from "@/components/auth-provider";
import { StoreSelector } from "@/components/store-selector";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

export function AppHeader() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const companyName =
    user.company?.trade_name || user.company?.legal_name || "Empresa";

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/80">
      <div className="flex h-14 items-center gap-3 px-4">
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          className="lg:hidden"
          aria-label="Abrir menu"
          onClick={() => setOpen(true)}
        >
          <Menu className="size-4" />
        </Button>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <SheetHeader className="sr-only">
              <SheetTitle>Menu</SheetTitle>
            </SheetHeader>
            <AppSidebar onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{companyName}</p>
          <p className="truncate text-xs text-muted-foreground">
            {user.full_name} · {user.profile}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StoreSelector />
          <Button type="button" variant="outline" size="sm" onClick={logout}>
            Sair
          </Button>
        </div>
      </div>
    </header>
  );
}
