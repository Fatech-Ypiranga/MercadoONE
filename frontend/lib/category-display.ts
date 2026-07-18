export type CategoryTreeItem = {
  id: number;
  parent_id?: number | null;
};

export type CategoryDisplayRow<T extends CategoryTreeItem> = {
  item: T;
  isChild: boolean;
};

/**
 * Build table rows for categories, preserving parent→child grouping when the
 * parent is present. Children whose parent is missing from the filtered set
 * are rendered once as indented fallback rows (no duplication).
 */
export function visibleCategoryRows<T extends CategoryTreeItem>(
  categories: T[],
): CategoryDisplayRow<T>[] {
  const ids = new Set(categories.map((category) => category.id));
  const roots = categories.filter((category) => category.parent_id == null);
  const childrenByParent = new Map<number, T[]>();
  const orphans: T[] = [];

  for (const category of categories) {
    if (category.parent_id == null) continue;
    if (ids.has(category.parent_id)) {
      const siblings = childrenByParent.get(category.parent_id) ?? [];
      siblings.push(category);
      childrenByParent.set(category.parent_id, siblings);
    } else {
      orphans.push(category);
    }
  }

  const rows: CategoryDisplayRow<T>[] = [];
  for (const root of roots) {
    rows.push({ item: root, isChild: false });
    for (const child of childrenByParent.get(root.id) ?? []) {
      rows.push({ item: child, isChild: true });
    }
  }
  for (const orphan of orphans) {
    rows.push({ item: orphan, isChild: true });
  }
  return rows;
}
