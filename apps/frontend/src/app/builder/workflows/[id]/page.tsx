"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  getWorkflowDefinition,
  publishWorkflowDefinition,
  saveWorkflowDefinition,
} from "@/lib/api";
import type { GraphLink, GraphNode } from "@/components/reactflow-canvas";

const StudioFullCanvas = dynamic(
  () => import("@/components/studio-full-canvas").then((m) => m.StudioFullCanvas),
  { loading: () => <div className="flex min-h-[40vh] items-center justify-center"><span className="text-xs" style={{ color: "var(--fx-muted)" }}>Loading canvas...</span></div> },
);

// Fallback scaffold for a brand-new / empty workflow only.
const DEFAULT_NODES: GraphNode[] = [
  { id: "trigger", title: "Trigger", type: "trigger", x: 70, y: 90 },
  { id: "agent", title: "Agent", type: "agent", x: 330, y: 90 },
  { id: "retrieval", title: "Retrieval", type: "retrieval", x: 610, y: 90 },
  { id: "guardrail", title: "Guardrail", type: "guardrail", x: 860, y: 90 },
  { id: "output", title: "Output", type: "output", x: 1110, y: 90 },
];
const DEFAULT_LINKS: GraphLink[] = [
  { from: "trigger", to: "agent" },
  { from: "agent", to: "retrieval" },
  { from: "retrieval", to: "guardrail" },
  { from: "guardrail", to: "output" },
];

export default function WorkflowStudioPage() {
  const params = useParams<{ id: string }>();
  const workflowId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [workflowName, setWorkflowName] = useState("Workflow");
  const [nodes, setNodes] = useState<GraphNode[] | null>(null);
  const [links, setLinks] = useState<GraphLink[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadWorkflow() {
      // single-definition fetch includes the persisted graph_json
      const def = await getWorkflowDefinition(workflowId);
      if (cancelled) {
        return;
      }
      if (def?.name) {
        setWorkflowName(def.name);
      }
      const graphNodes = def?.graph_json?.nodes ?? [];
      if (graphNodes.length) {
        setNodes(graphNodes as GraphNode[]);
        setLinks((def?.graph_json?.links ?? []) as GraphLink[]);
      } else {
        setNodes(DEFAULT_NODES);
        setLinks(DEFAULT_LINKS);
      }
    }

    void loadWorkflow();

    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const stableWorkflowName = useMemo(() => workflowName || "Workflow", [workflowName]);

  if (nodes === null) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <span className="text-xs" style={{ color: "var(--fx-muted)" }}>Loading workflow...</span>
      </div>
    );
  }

  return (
    <StudioFullCanvas
      entityType="workflow"
      entityId={workflowId}
      entityName={stableWorkflowName}
      description="Compose orchestration logic directly on canvas; this graph is persisted and executed by FastAPI orchestration services."
      initialNodes={nodes}
      initialLinks={links}
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
