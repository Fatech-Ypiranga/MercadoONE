"use client";

import { flexRender, type Table as TanStackTable } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function align(meta: unknown) {
  return (meta as { align?: string } | undefined)?.align === "right" ? "text-right" : undefined;
}

export function DataTable<T>({ table }: { table: TanStackTable<T> }) {
  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => {
              const sortDir = header.column.getIsSorted();
              return (
                <TableHead key={header.id} className={align(header.column.columnDef.meta)}>
                  {header.column.getCanSort() ? (
                    <button
                      type="button"
                      onClick={header.column.getToggleSortingHandler()}
                      className={`inline-flex items-center gap-1 ${
                        align(header.column.columnDef.meta) ? "flex-row-reverse" : ""
                      }`}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sortDir === "asc" ? (
                        <ArrowUp className="size-3" />
                      ) : sortDir === "desc" ? (
                        <ArrowDown className="size-3" />
                      ) : (
                        <ArrowUpDown className="size-3 opacity-40" />
                      )}
                    </button>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </TableHead>
              );
            })}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.map((row) => (
          <TableRow key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <TableCell key={cell.id} className={align(cell.column.columnDef.meta)}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
