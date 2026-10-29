import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  COLOR_VISION_INIT_SCRIPT,
  COLOR_VISION_MODES,
  parseColorVisionMode,
} from "./color-vision.ts";

describe("parseColorVisionMode", () => {
  it("accepts every known mode", () => {
    for (const mode of COLOR_VISION_MODES) {
      assert.equal(parseColorVisionMode(mode), mode);
    }
  });

  it("falls back to none for unknown or missing values", () => {
    assert.equal(parseColorVisionMode(null), "none");
    assert.equal(parseColorVisionMode(""), "none");
    assert.equal(parseColorVisionMode("daltonico"), "none");
  });
});

describe("COLOR_VISION_INIT_SCRIPT", () => {
  function run(stored: string | null) {
    const attrs: Record<string, string> = {};
    const fn = new Function("localStorage", "document", COLOR_VISION_INIT_SCRIPT);
    fn(
      { getItem: () => stored },
      { documentElement: { setAttribute: (k: string, v: string) => (attrs[k] = v) } },
    );
    return attrs["data-cvd"];
  }

  it("applies a stored mode before hydration", () => {
    assert.equal(run("tritanopia"), "tritanopia");
  });

  it("ignores none and invalid values", () => {
    assert.equal(run("none"), undefined);
    assert.equal(run("<script>"), undefined);
    assert.equal(run(null), undefined);
  });
});
