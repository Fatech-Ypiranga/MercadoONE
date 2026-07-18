import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { visibleCategoryRows } from "./category-display.ts";

describe("visibleCategoryRows", () => {
  it("keeps normal parent/child grouping without duplication", () => {
    const rows = visibleCategoryRows([
      { id: 1, parent_id: null, name: "Eletronicos" },
      { id: 2, parent_id: 1, name: "Mouses" },
    ]);

    assert.deepEqual(
      rows.map((row) => [row.item.id, row.isChild]),
      [
        [1, false],
        [2, true],
      ],
    );
  });

  it("renders orphaned children as indented fallback when parent is absent", () => {
    const rows = visibleCategoryRows([
      { id: 2, parent_id: 99, name: "Mouses" },
      { id: 3, parent_id: null, name: "Moveis" },
    ]);

    assert.deepEqual(
      rows.map((row) => [row.item.id, row.isChild]),
      [
        [3, false],
        [2, true],
      ],
    );
  });

  it("does not duplicate a child that already appears under its parent", () => {
    const rows = visibleCategoryRows([
      { id: 1, parent_id: null, name: "Eletronicos" },
      { id: 2, parent_id: 1, name: "Mouses" },
    ]);

    assert.equal(rows.filter((row) => row.item.id === 2).length, 1);
  });
});
