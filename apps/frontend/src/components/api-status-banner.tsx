"use client";

import { useEffect, useState } from "react";
import { onApiStatusChange } from "@/lib/api";

export function ApiStatusBanner() {
  const [connected, setConnected] = useState(true);

  useEffect(() => {
    return onApiStatusChange(setConnected);
  }, []);

  if (connected) return null;

  return (
    <div
      role="alert"
      className="flex items-center gap-2 px-4 py-2 text-xs font-medium"
      style={{
        background: "hsl(var(--state-warning) / 0.12)",
        borderBottom: "1px solid hsl(var(--state-warning) / 0.3)",
        color: "hsl(var(--foreground))",
      }}
    >
      <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="hsl(var(--state-warning))" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <path d="M12 9v4M12 17h.01" />
      </svg>
      <span>Backend unreachable &mdash; showing cached or fallback data. Check that the API server is running.</span>
    </div>
  );
}
