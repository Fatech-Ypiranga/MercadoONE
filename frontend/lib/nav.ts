import type { LucideIcon } from "lucide-react";
import {
  Building2,
  ClipboardList,
  FileBarChart,
  FolderKanban,
  LayoutDashboard,
  LayoutGrid,
  Package,
  ScrollText,
  Store,
  Tags,
  Truck,
  Users,
  Warehouse,
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
  /** Só exibir quando a empresa tem filiais habilitadas. */
  requiresBranches?: boolean;
};

export type NavSection = {
  title: string;
  icon: LucideIcon;
  items: NavItem[];
};

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Principal",
    icon: LayoutGrid,
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
    icon: FolderKanban,
    items: [
      { href: "/products", label: "Produtos", icon: Package, module: "products" },
      { href: "/categories", label: "Categorias", icon: Tags, module: "categories" },
      { href: "/customers", label: "Clientes", icon: Users, module: "customers" },
      { href: "/suppliers", label: "Fornecedores", icon: Truck, module: "suppliers" },
    ],
  },
  {
    title: "Organização",
    icon: Building2,
    items: [
      {
        href: "/company",
        label: "Minha empresa",
        icon: Building2,
        module: "companies",
      },
      {
        href: "/branches",
        label: "Filiais",
        icon: Building2,
        module: "branches",
        action: "write",
        requiresBranches: true,
      },
      { href: "/stores", label: "Lojas", icon: Store, module: "stores", action: "write" },
      { href: "/users", label: "Usuários", icon: Users, module: "users" },
      { href: "/audit", label: "Auditoria", icon: ScrollText, module: "audit" },
    ],
  },
];

export function visibleNavSections(
  profile: UserProfile,
  options: { hasBranches?: boolean } = {},
): NavSection[] {
  const hasBranches = options.hasBranches ?? false;
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => {
      if (item.requiresBranches && !hasBranches) return false;
      if (!item.module) return true;
      return can(profile, item.module, item.action ?? "read");
    }),
  })).filter((section) => section.items.length > 0);
}
