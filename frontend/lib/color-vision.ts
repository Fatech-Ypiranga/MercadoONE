/**
 * Modos de visão de cores (daltonismo). O modo ativo vai no atributo
 * `data-cvd` do <html>; `globals.css` troca as cores semânticas
 * (sucesso, erro, gráficos) por paletas distinguíveis para cada tipo.
 */
export const COLOR_VISION_MODES = [
  "none",
  "protanopia",
  "deuteranopia",
  "tritanopia",
  "achromatopsia",
] as const;

export type ColorVisionMode = (typeof COLOR_VISION_MODES)[number];

export const COLOR_VISION_STORAGE_KEY = "mercadoone:color-vision";

export const COLOR_VISION_OPTIONS: Record<
  ColorVisionMode,
  { label: string; description: string }
> = {
  none: { label: "Padrão", description: "Cores originais" },
  protanopia: {
    label: "Protanopia",
    description: "Vermelho (inclui protanomalia)",
  },
  deuteranopia: {
    label: "Deuteranopia",
    description: "Verde (inclui deuteranomalia)",
  },
  tritanopia: {
    label: "Tritanopia",
    description: "Azul/amarelo (inclui tritanomalia)",
  },
  achromatopsia: {
    label: "Acromatopsia",
    description: "Sem cores (monocromacia)",
  },
};

export function parseColorVisionMode(value: unknown): ColorVisionMode {
  return COLOR_VISION_MODES.includes(value as ColorVisionMode)
    ? (value as ColorVisionMode)
    : "none";
}

export function applyColorVisionMode(mode: ColorVisionMode) {
  const root = document.documentElement;
  if (mode === "none") root.removeAttribute("data-cvd");
  else root.setAttribute("data-cvd", mode);
}

/**
 * Script inline executado antes da hidratação para aplicar o modo salvo
 * sem "piscar" as cores padrão no carregamento.
 */
export const COLOR_VISION_INIT_SCRIPT = `try{var m=localStorage.getItem(${JSON.stringify(
  COLOR_VISION_STORAGE_KEY,
)});if(${JSON.stringify(COLOR_VISION_MODES.filter((m) => m !== "none"))}.indexOf(m)>-1)document.documentElement.setAttribute("data-cvd",m)}catch(e){}`;
