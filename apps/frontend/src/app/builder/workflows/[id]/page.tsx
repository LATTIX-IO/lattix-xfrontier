"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getWorkflowDefinitions, publishWorkflowDefinition, saveWorkflowDefinition } from "@/lib/api";

const StudioFullCanvas = dynamic(
  () => import("@/components/studio-full-canvas").then((m) => m.StudioFullCanvas),
  { loading: () => <div className="flex min-h-[40vh] items-center justify-center"><span className="text-xs" style={{ color: "var(--fx-muted)" }}>Loading canvas...</span></div> },
);

export default function WorkflowStudioPage() {
  const params = useParams<{ id: string }>();
  const workflowId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [workflowName, setWorkflowName] = useState("Workflow");

  useEffect(() => {
    let cancelled = false;

    async function loadWorkflow() {
      const workflows = await getWorkflowDefinitions();
      if (cancelled) {
        return;
      }
      const match = workflows.find((workflow) => workflow.id === workflowId);
      if (match?.name) {
        setWorkflowName(match.name);
      }
    }

    void loadWorkflow();

    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const stableWorkflowName = useMemo(() => workflowName || "Workflow", [workflowName]);

  return (
    <StudioFullCanvas
      entityType="workflow"
      entityId={workflowId}
      entityName={stableWorkflowName}
      description="Compose orchestration logic directly on canvas; this graph is persisted and executed by FastAPI orchestration services."
      initialNodes={[
        { id: "trigger", title: "Trigger", type: "trigger", x: 70, y: 90 },
        { id: "agent", title: "Agent", type: "agent", x: 330, y: 90 },
        { id: "retrieval", title: "Retrieval", type: "retrieval", x: 610, y: 90 },
        { id: "guardrail", title: "Guardrail", type: "guardrail", x: 860, y: 90 },
        { id: "output", title: "Output", type: "output", x: 1110, y: 90 },
      ]}
      initialLinks={[
        { from: "trigger", to: "agent" },
        { from: "agent", to: "retrieval" },
        { from: "retrieval", to: "guardrail" },
        { from: "guardrail", to: "output" },
      ]}
      onSave={async (graph) => {
        await saveWorkflowDefinition({
          id: workflowId,
          graph_json: graph,
        });
      }}
      onPublish={async () => {
        await publishWorkflowDefinition(workflowId);
      }}
    />
  );
}
