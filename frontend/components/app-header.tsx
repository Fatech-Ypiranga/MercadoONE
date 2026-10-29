"use client";

import { Menu, Search } from "lucide-react";
import { useState } from "react";

import { AppSidebar } from "@/components/app-sidebar";
import { useAuth } from "@/components/auth-provider";
import { ChangePasswordDialog } from "@/components/change-password-dialog";
import { ColorVisionSelect } from "@/components/color-vision-select";
import { openCommandPalette } from "@/components/command-palette";
import { StoreSelector } from "@/components/store-selector";
import { ThemeToggle } from "@/components/theme-toggle";
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
          aria-expanded={open}
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

        <button
          type="button"
          onClick={openCommandPalette}
          aria-keyshortcuts="Control+K Meta+K"
          className="hidden h-9 w-64 items-center gap-2 rounded-md border border-input bg-background px-3 text-sm text-muted-foreground transition-colors hover:border-ring sm:flex"
        >
          <Search className="size-4 shrink-0" />
          <span className="flex-1 text-left">Buscar…</span>
          <span
            aria-hidden
            className="rounded-md border border-border px-1.5 py-0.5 text-[11px] font-medium"
          >
            ⌘K
          </span>
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{companyName}</p>
          <p className="truncate text-xs text-muted-foreground">
            {user.full_name} · {user.profile}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <ColorVisionSelect />
          <StoreSelector />
          <ChangePasswordDialog />
          <Button type="button" variant="outline" size="sm" onClick={logout}>
            Sair
          </Button>
        </div>
      </div>
    </header>
  );
}
