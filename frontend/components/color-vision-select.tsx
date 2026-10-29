"use client";

import { Eye } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import {
  applyColorVisionMode,
  COLOR_VISION_MODES,
  COLOR_VISION_OPTIONS,
  COLOR_VISION_STORAGE_KEY,
  parseColorVisionMode,
  type ColorVisionMode,
} from "@/lib/color-vision";

export function ColorVisionSelect() {
  const [mode, setMode] = useState<ColorVisionMode>("none");

  useEffect(() => {
    setMode(parseColorVisionMode(localStorage.getItem(COLOR_VISION_STORAGE_KEY)));
  }, []);

  function change(next: ColorVisionMode) {
    setMode(next);
    applyColorVisionMode(next);
    try {
      if (next === "none") localStorage.removeItem(COLOR_VISION_STORAGE_KEY);
      else localStorage.setItem(COLOR_VISION_STORAGE_KEY, next);
    } catch {
      // Armazenamento indisponível (ex.: modo privado): aplica só nesta sessão.
    }
  }

  return (
    <Select value={mode} onValueChange={(next) => change(parseColorVisionMode(next))}>
      <SelectTrigger
        size="sm"
        aria-label={`Modo para daltonismo: ${COLOR_VISION_OPTIONS[mode].label}`}
        title="Modo para daltonismo"
        className={mode !== "none" ? "border-ring text-foreground" : undefined}
      >
        <Eye className="size-4" aria-hidden />
      </SelectTrigger>
      <SelectContent align="end" alignItemWithTrigger={false} className="w-64">
        {COLOR_VISION_MODES.map((value) => (
          <SelectItem key={value} value={value}>
            <span className="flex flex-col">
              <span>{COLOR_VISION_OPTIONS[value].label}</span>
              <span className="text-xs text-muted-foreground">
                {COLOR_VISION_OPTIONS[value].description}
              </span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
