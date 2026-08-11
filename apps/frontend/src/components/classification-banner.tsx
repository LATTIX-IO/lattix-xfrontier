"use client";

import { useSyncExternalStore } from "react";

export type ClassificationPreset =
  | "neutral"
  | "confidential"
  | "restricted"
  | "secret"
  | "topsecret"
  | "success";

type PresetStyles = {
  background: string;
  foreground: string;
  border: string;
};

export const CLASSIFICATION_PRESETS: Record<ClassificationPreset, PresetStyles> = {
  neutral: {
    background: "hsl(210 16% 93%)",
    foreground: "hsl(220 14% 24%)",
    border: "hsl(220 14% 89%)",
  },
  confidential: {
    background: "hsl(35 95% 52% / 0.18)",
    foreground: "hsl(32 85% 32%)",
    border: "hsl(35 95% 52% / 0.5)",
  },
  restricted: {
    background: "hsl(358 75% 56% / 0.14)",
    foreground: "hsl(358 65% 38%)",
    border: "hsl(358 75% 56% / 0.4)",
  },
  secret: {
    background: "hsl(220 85% 52% / 0.12)",
    foreground: "hsl(220 85% 34%)",
    border: "hsl(220 85% 52% / 0.4)",
  },
  topsecret: {
    background: "hsl(220 14% 14%)",
    foreground: "hsl(35 95% 62%)",
    border: "hsl(220 14% 14%)",
  },
  success: {
    background: "hsl(145 55% 46% / 0.14)",
    foreground: "hsl(145 55% 26%)",
    border: "hsl(145 55% 46% / 0.4)",
  },
};

export const DEFAULT_CLASSIFICATION_TEXT =
  "Internal · Operational Console · Zero Trust Enforced";
export const DEFAULT_CLASSIFICATION_PRESET: ClassificationPreset = "success";

const STORAGE_KEY = "frontier-classification-banner";

export type ClassificationBannerState = {
  enabled: boolean;
  text: string;
  preset: ClassificationPreset;
};

const DEFAULT_STATE: ClassificationBannerState = {
  enabled: true,
  text: DEFAULT_CLASSIFICATION_TEXT,
  preset: DEFAULT_CLASSIFICATION_PRESET,
};

export function readClassificationBannerState(): ClassificationBannerState {
  if (typeof window === "undefined") {
    return DEFAULT_STATE;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_STATE;
    const parsed = JSON.parse(raw) as Partial<ClassificationBannerState>;
    const preset: ClassificationPreset =
      parsed.preset && parsed.preset in CLASSIFICATION_PRESETS
        ? (parsed.preset as ClassificationPreset)
        : DEFAULT_CLASSIFICATION_PRESET;
    return {
      enabled: parsed.enabled ?? DEFAULT_STATE.enabled,
      text: typeof parsed.text === "string" && parsed.text.trim().length > 0
        ? parsed.text
        : DEFAULT_STATE.text,
      preset,
    };
  } catch {
    return DEFAULT_STATE;
  }
}

export function writeClassificationBannerState(state: ClassificationBannerState) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    window.dispatchEvent(new CustomEvent("frontier-classification-change", { detail: state }));
  } catch {
    /* ignore storage failures */
  }
}

let cachedSnapshot: ClassificationBannerState | null = null;

function getClientSnapshot(): ClassificationBannerState {
  if (cachedSnapshot) return cachedSnapshot;
  cachedSnapshot = readClassificationBannerState();
  return cachedSnapshot;
}

function getServerSnapshot(): ClassificationBannerState {
  return DEFAULT_STATE;
}

function subscribe(callback: () => void): () => void {
  const handler = () => {
    cachedSnapshot = readClassificationBannerState();
    callback();
  };
  window.addEventListener("frontier-classification-change", handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener("frontier-classification-change", handler);
    window.removeEventListener("storage", handler);
  };
}

export function useClassificationBanner(): [
  ClassificationBannerState,
  (next: Partial<ClassificationBannerState>) => void,
] {
  const state = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);

  const update = (next: Partial<ClassificationBannerState>) => {
    const current = readClassificationBannerState();
    const merged: ClassificationBannerState = { ...current, ...next };
    writeClassificationBannerState(merged);
    cachedSnapshot = merged;
  };

  return [state, update];
}

export function ClassificationBanner({
  state,
  top = 0,
  height = 32,
}: {
  state: ClassificationBannerState;
  top?: number;
  height?: number;
}) {
  if (!state.enabled) return null;
  const preset = CLASSIFICATION_PRESETS[state.preset] ?? CLASSIFICATION_PRESETS.neutral;

  return (
    <div
      role="note"
      aria-label="Classification banner"
      className="fixed inset-x-0 z-40 flex items-center justify-center px-5 text-[11px] font-semibold uppercase tracking-[0.1em]"
      style={{
        top: `${top}px`,
        height: `${height}px`,
        background: preset.background,
        color: preset.foreground,
        borderBottom: `1px solid ${preset.border}`,
        fontFamily: "var(--font-space-mono), 'Space Mono', monospace",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      <span className="min-w-0 truncate">{state.text}</span>
    </div>
  );
}
