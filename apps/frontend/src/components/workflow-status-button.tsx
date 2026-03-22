"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { archiveWorkflowDefinition, publishWorkflowDefinition } from "@/lib/api";

type Props = {
  workflowId: string;
  status: "draft" | "published" | "archived";
};

export function WorkflowStatusButton({ workflowId, status }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function runAction() {
    setBusy(true);
    try {
      if (status === "published") {
        await archiveWorkflowDefinition(workflowId);
      } else {
        await publishWorkflowDefinition(workflowId);
      }
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const isArchive = status === "published";

  return (
    <button
      onClick={runAction}
      disabled={busy}
      className={(isArchive ? "fx-btn-secondary" : "fx-btn-primary") + " px-2.5 py-1 text-xs font-medium disabled:opacity-60"}
    >
      {busy ? (isArchive ? "Archiving..." : "Publishing...") : (isArchive ? "Archive" : "Publish")}
    </button>
  );
}
