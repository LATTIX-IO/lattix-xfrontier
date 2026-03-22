"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { publishWorkflowDefinition, saveWorkflowDefinition } from "@/lib/api";
import { SecurityScopeEditor } from "@/components/security-scope-editor";
import type { GraphLink, GraphNode } from "@/components/reactflow-canvas";
import type { GeneratedCodeArtifact, SecurityScopeConfig } from "@/types/frontier";

const StudioFullCanvas = dynamic(
  () => import("@/components/studio-full-canvas").then((m) => m.StudioFullCanvas),
  { loading: () => <div className="flex min-h-[40vh] items-center justify-center"><span className="text-xs" style={{ color: "var(--fx-muted)" }}>Loading canvas...</span></div> },
);

type Props = {
  workflowId: string;
  workflowName: string;
  initialGraph?: {
    nodes?: GraphNode[];
    links?: GraphLink[];
  };
  initialSecurity?: SecurityScopeConfig;
  initialGeneratedArtifacts?: GeneratedCodeArtifact[];
};

export function WorkflowStudioClient({ workflowId, workflowName, initialGraph, initialSecurity, initialGeneratedArtifacts }: Props) {
  const [securityConfig, setSecurityConfig] = useState<SecurityScopeConfig>(initialSecurity ?? {});

  const defaultNodes: GraphNode[] = [
    { id: "trigger", title: "Trigger", type: "trigger", x: 70, y: 90 },
    { id: "agent", title: "Agent", type: "agent", x: 330, y: 90 },
    { id: "retrieval", title: "Retrieval", type: "retrieval", x: 610, y: 90 },
    { id: "guardrail", title: "Guardrail", type: "guardrail", x: 860, y: 90 },
    { id: "output", title: "Output", type: "output", x: 1110, y: 90 },
  ];
  const defaultLinks: GraphLink[] = [
    { from: "trigger", to: "agent" },
    { from: "agent", to: "retrieval" },
    { from: "retrieval", to: "guardrail" },
    { from: "guardrail", to: "output" },
  ];

  const initialNodes = initialGraph?.nodes?.length ? initialGraph.nodes : defaultNodes;
  const initialLinks = initialGraph?.links?.length ? initialGraph.links : defaultLinks;

  return (
    <StudioFullCanvas
      entityType="workflow"
      entityId={workflowId}
      entityName={workflowName}
      builderMode="standard"
      description="Compose orchestration logic directly on canvas; this graph is persisted and executed by FastAPI orchestration services."
      initialNodes={initialNodes}
      initialLinks={initialLinks}
      initialGeneratedArtifacts={initialGeneratedArtifacts}
      rightSidebarSlot={
        <SecurityScopeEditor
          entityType="workflow"
          entityId={workflowId}
          entityName={workflowName}
          value={securityConfig}
          onChange={setSecurityConfig}
          onSave={async () => {
            await saveWorkflowDefinition({
              id: workflowId,
              name: workflowName,
              security_config: securityConfig,
            });
          }}
        />
      }
      onSave={async (graph) => {
        await saveWorkflowDefinition({
          id: workflowId,
          name: workflowName,
          graph_json: graph,
          security_config: securityConfig,
        });
      }}
      onPublish={async () => {
        await publishWorkflowDefinition(workflowId);
      }}
    />
  );
}
