"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import { visibleNavSections } from "@/lib/nav";
import { cn } from "@/lib/utils";

function isItemActive(pathname: string, href: string) {
  return pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
}

export function NavRail() {
  const pathname = usePathname();
  const { user } = useAuth();

  if (!user) return null;

  const sections = visibleNavSections(user.profile, {
    hasBranches: Boolean(user.company?.has_branches),
  });

  const activeSection =
    sections.find((section) => section.items.some((item) => isItemActive(pathname, item.href))) ??
    sections[0];

  if (!activeSection) return null;

  return (
    <div className="hidden lg:flex">
      {/* Icon rail */}
      <div className="flex w-16 shrink-0 flex-col items-center gap-2 bg-sidebar py-4">
        <div className="mb-2 flex size-8 items-center justify-center rounded-lg bg-sidebar-primary text-[13px] font-bold text-sidebar-primary-foreground">
          M1
        </div>
        <div className="mb-1 h-px w-8 bg-sidebar-border" />
        {sections.map((section) => {
          const Icon = section.icon;
          const active = section.title === activeSection.title;
          return (
            <Link
              key={section.title}
              href={section.items[0].href}
              title={section.title}
              className={cn(
                "flex size-10 items-center justify-center rounded-lg transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/55 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
            >
              <Icon className="size-[18px]" />
            </Link>
          );
        })}
      </div>

      {/* Contextual sub-rail */}
      <div className="w-52 shrink-0 border-r border-border bg-card px-3 py-4">
        <div className="mb-5 px-2">
          <p className="text-sm font-semibold tracking-tight">MercadoONE</p>
          <p className="truncate text-xs text-muted-foreground">
            {user.company?.trade_name || user.company?.legal_name || "Empresa"}
          </p>
        </div>

        <p className="px-2 pb-1.5 text-[10px] font-semibold tracking-wide text-muted-foreground/80 uppercase">
          {activeSection.title}
        </p>
        <ul className="space-y-0.5">
          {activeSection.items.map((item) => {
            const active = isItemActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-2 py-[7px] text-[13px] transition-colors",
                    active
                      ? "bg-accent font-medium text-accent-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
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
    </div>
  );
}
