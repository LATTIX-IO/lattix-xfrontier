"use client";

import Link from "next/link";
import type { AppMode } from "@/types/frontier";

export function ModeSwitch({
  activeMode = "user",
  canAccessBuilder = false,
}: {
  activeMode?: AppMode;
  canAccessBuilder?: boolean;
}) {
  const inBuilder = activeMode === "builder" && canAccessBuilder;

  return (
    <div
      className="inline-flex items-center gap-0.5 rounded-[12px] border border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--muted))_70%,white_30%)] p-0.5 shadow-[var(--fx-shadow-soft)]"
    >
      <Link
        href="/inbox"
        className={`rounded-[10px] px-3 py-1.5 text-[11px] font-medium no-underline transition ${
          !inBuilder
            ? "bg-[hsl(var(--card))] text-[hsl(var(--foreground))] border border-[var(--ui-border)]"
            : "border border-transparent text-[var(--fx-muted)] hover:text-[hsl(var(--foreground))] hover:bg-[var(--fx-nav-hover)]"
        }`}
      >
        User
      </Link>
      <Link
        href="/builder/workflows"
        aria-disabled={!canAccessBuilder}
        className={`rounded-[10px] px-3 py-1.5 text-[11px] font-medium no-underline transition ${
          !canAccessBuilder
            ? "cursor-not-allowed border border-transparent text-[var(--fx-muted)] opacity-70"
            : inBuilder
              ? "bg-[hsl(var(--card))] text-[hsl(var(--foreground))] border border-[var(--ui-border)]"
              : "border border-transparent text-[var(--fx-muted)] hover:text-[hsl(var(--foreground))] hover:bg-[var(--fx-nav-hover)]"
        }`}
        title={canAccessBuilder ? "Switch to builder mode" : "Builder mode requires a builder-capable identity."}
        onClick={(event) => {
          if (!canAccessBuilder) {
            event.preventDefault();
          }
        }}
      >
        Builder
      </Link>
    </div>
  );
}
