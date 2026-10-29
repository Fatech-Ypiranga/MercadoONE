"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import { visibleNavSections } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();

  if (!user) return null;

  const sections = visibleNavSections(user.profile, {
    hasBranches: Boolean(user.company?.has_branches),
  });

  return (
    <nav aria-label="Menu principal" className="flex h-full flex-col gap-6 px-3 py-4">
      <div className="px-2">
        <p className="text-sm font-semibold tracking-tight">MercadoONE</p>
        <p className="truncate text-xs text-muted-foreground">
          {user.company?.trade_name || user.company?.legal_name || "Empresa"}
        </p>
      </div>

      {sections.map((section) => (
        <div key={section.title} className="space-y-1">
          <p className="px-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            {section.title}
          </p>
          <ul className="space-y-0.5">
            {section.items.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
              const Icon = item.icon;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors",
                      active
                        ? "bg-muted font-medium text-foreground"
                        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                    )}
                  >
                    <Icon className="size-4 shrink-0" />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
