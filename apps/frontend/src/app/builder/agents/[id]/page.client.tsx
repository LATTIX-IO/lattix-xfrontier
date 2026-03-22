"use client";

import dynamic from "next/dynamic";
import { publishAgentDefinition, saveAgentDefinition } from "@/lib/api";
import type { GraphLink, GraphNode } from "@/components/reactflow-canvas";

const StudioFullCanvas = dynamic(
  () => import("@/components/studio-full-canvas").then((m) => m.StudioFullCanvas),
  { loading: () => <div className="flex min-h-[40vh] items-center justify-center"><span className="text-xs" style={{ color: "var(--fx-muted)" }}>Loading canvas...</span></div> },
);

type Props = {
  agentId: string;
  agentName: string;
  initialGraph?: {
    nodes?: GraphNode[];
    links?: GraphLink[];
  };
};

export function AgentStudioClient({ agentId, agentName, initialGraph }: Props) {
  const defaultNodes: GraphNode[] = [
    { id: "trigger", title: "Trigger", type: "trigger", x: 70, y: 90 },
    { id: "agent", title: "Agent", type: "agent", x: 330, y: 90 },
    { id: "tool-call", title: "Tool / API Call", type: "tool-call", x: 610, y: 90 },
    { id: "output", title: "Output", type: "output", x: 860, y: 90 },
  ];
  const defaultLinks: GraphLink[] = [
    { from: "trigger", to: "agent" },
    { from: "agent", to: "tool-call" },
    { from: "tool-call", to: "output" },
  ];

  const initialNodes = initialGraph?.nodes?.length ? initialGraph.nodes : defaultNodes;
  const initialLinks = initialGraph?.links?.length ? initialGraph.links : defaultLinks;

  return (
    <StudioFullCanvas
      entityType="agent"
      entityId={agentId}
      entityName={agentName}
      description="Model the full execution logic in this canvas; FastAPI consumes serialized node/edge definitions as the source of truth."
      initialNodes={initialNodes}
      initialLinks={initialLinks}
      onSave={async (graph) => {
        await saveAgentDefinition({
          id: agentId,
          name: agentName,
          config_json: {
            schema_version: "frontier-agent-definition/1.0",
            source_agent_id: agentId,
            meta: {
              name: agentName,
            },
            runtime: {
              model_defaults: {
                provider: "openai",
                model: "gpt-5",
                temperature: 0.2,
              },
            },
            reasoning: {
              strategy: "plan-execute-review",
              self_review: true,
              expose_internal_reasoning: false,
            },
            knowledge: {
              retrieval_mode: "hybrid",
              sources: ["kb://default"],
              top_k: 6,
            },
            integrations: {
              framework_runtime_adapters: {
                langgraph: "orchestration",
                langchain: "retrieval-and-tools",
                "semantic-kernel": "plugins-and-mcp",
                autogen: "multi-agent-collaboration",
              },
            },
            mcp: {
              enabled: true,
            },
            a2a: {
              enabled: true,
              require_signed_messages: true,
            },
            tools: {
              require_human_approval_for_high_risk: true,
            },
            memory: {
              default_scope: "session",
              allow_scopes: ["run", "session", "user", "tenant", "agent", "workflow", "global"],
            },
            guardrails: {
              enable_platform_signals: true,
              platform_signal_enforcement: "block_high",
              platform_signal_detect_prompt_injection: true,
              platform_signal_detect_pii: true,
              platform_signal_detect_command_injection: true,
              platform_signal_detect_exfiltration: true,
            },
            graph_json: graph,
          },
        });
      }}
      onPublish={async () => {
        await publishAgentDefinition(agentId);
      }}
    />
  );
}
