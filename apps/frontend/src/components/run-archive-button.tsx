"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { archiveWorkflowRun } from "@/lib/api";

type Props = {
  runId: string;
  buttonClassName?: string;
  label?: string;
};

export function RunArchiveButton({ runId, buttonClassName, label }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function archiveRun() {
    setBusy(true);
    try {
      await archiveWorkflowRun(runId);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={archiveRun}
      disabled={busy}
      className={buttonClassName ?? "fx-btn-secondary px-2.5 py-1 text-xs font-medium disabled:opacity-60"}
    >
      {busy ? "Archiving..." : (label ?? "Archive")}
    </button>
  );
}
