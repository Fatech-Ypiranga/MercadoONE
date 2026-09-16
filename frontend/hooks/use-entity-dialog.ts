import { useState } from "react";

/**
 * Shared open/editing/error state for CRUD dialogs — the same trio was
 * hand-rolled with useState in every list page (products, users, customers,
 * purchases, suppliers, stock, categories). Deliberately does not touch
 * mutation logic or form fields, since those differ per entity.
 */
export function useEntityDialog<TEntity>() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TEntity | null>(null);
  const [error, setError] = useState<string | null>(null);

  function openCreate() {
    setEditing(null);
    setError(null);
    setOpen(true);
  }

  function openEdit(entity: TEntity) {
    setEditing(entity);
    setError(null);
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setEditing(null);
    setError(null);
  }

  return { open, setOpen, editing, error, setError, openCreate, openEdit, close };
}
