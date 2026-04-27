"use client";

export type ClassificationPreset =
  | "neutral"
  | "confidential"
  | "restricted"
  | "secret"
  | "topsecret"
  | "success";

type PresetSpec = {
  background: string;
  foreground: string;
  borderColor: string;
  label: string;
};

export const CLASSIFICATION_PRESETS: Record<ClassificationPreset, PresetSpec> = {
  neutral: {
    background: "hsl(210 16% 93%)",
    foreground: "hsl(220 14% 24%)",
    borderColor: "hsl(220 14% 89%)",
    label: "Neutral",
  },
  confidential: {
    background: "hsl(35 95% 52% / 0.18)",
    foreground: "hsl(32 85% 32%)",
    borderColor: "hsl(35 95% 52% / 0.5)",
    label: "Confidential",
  },
  restricted: {
    background: "hsl(358 75% 56% / 0.14)",
    foreground: "hsl(358 65% 38%)",
    borderColor: "hsl(358 75% 56% / 0.4)",
    label: "Restricted",
  },
  secret: {
    background: "hsl(220 85% 52% / 0.12)",
    foreground: "hsl(220 85% 34%)",
    borderColor: "hsl(220 85% 52% / 0.4)",
    label: "Secret",
  },
  topsecret: {
    background: "hsl(220 14% 14%)",
    foreground: "hsl(35 95% 62%)",
    borderColor: "hsl(220 14% 14%)",
    label: "Top Secret",
  },
  success: {
    background: "hsl(145 55% 46% / 0.14)",
    foreground: "hsl(145 55% 26%)",
    borderColor: "hsl(145 55% 46% / 0.4)",
    label: "All Clear",
  },
};

export const CLASSIFICATION_BANNER_HEIGHT = 32;

export function ClassificationBanner({
  text,
  preset = "success",
  height = CLASSIFICATION_BANNER_HEIGHT,
  top = 0,
}: {
  text: string;
  preset?: ClassificationPreset;
  height?: number;
  top?: number;
}) {
  const spec = CLASSIFICATION_PRESETS[preset] ?? CLASSIFICATION_PRESETS.neutral;

  return (
    <div
      className="fixed inset-x-0 z-40 flex items-center justify-center px-5 text-[10px] font-bold uppercase tracking-[0.1em]"
      style={{
        top: `${top}px`,
        height: `${height}px`,
        background: spec.background,
        color: spec.foreground,
        borderBottom: `1px solid ${spec.borderColor}`,
        fontFamily: "var(--font-space-mono), 'Space Mono', monospace",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      {text}
    </div>
  );
}
