import type { LucideIcon } from "lucide-react";
import {
  ClipboardList,
  FileBarChart,
  LayoutDashboard,
  Package,
  ScrollText,
  Store,
  Tags,
  Truck,
  Users,
  Warehouse,
  Building2,
} from "lucide-react";

import type { UserProfile } from "@/lib/permissions";
import { can } from "@/lib/permissions";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  module?: string;
  /** Ação exigida para aparecer no menu (default: read). */
  action?: "read" | "write";
};

export type NavSection = {
  title: string;
  items: NavItem[];
};

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Principal",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/sales", label: "Vendas", icon: ClipboardList, module: "sales" },
      { href: "/stock", label: "Estoque", icon: Warehouse, module: "stock" },
      { href: "/purchases", label: "Compras", icon: Truck, module: "purchases" },
      { href: "/reports", label: "Relatórios", icon: FileBarChart, module: "reports" },
    ],
  },
  {
    title: "Cadastros",
    items: [
      { href: "/products", label: "Produtos", icon: Package, module: "products" },
      { href: "/categories", label: "Categorias", icon: Tags, module: "categories" },
      { href: "/customers", label: "Clientes", icon: Users, module: "customers" },
      { href: "/suppliers", label: "Fornecedores", icon: Truck, module: "suppliers" },
    ],
  },
  {
    title: "Organização",
    items: [
      {
        href: "/branches",
        label: "Filiais",
        icon: Building2,
        module: "branches",
        action: "write",
      },
      { href: "/stores", label: "Lojas", icon: Store, module: "stores", action: "write" },
      { href: "/users", label: "Usuários", icon: Users, module: "users" },
      { href: "/audit", label: "Auditoria", icon: ScrollText, module: "audit" },
    ],
  },
];

export function visibleNavSections(profile: UserProfile): NavSection[] {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => {
      if (!item.module) return true;
      return can(profile, item.module, item.action ?? "read");
    }),
  })).filter((section) => section.items.length > 0);
}
