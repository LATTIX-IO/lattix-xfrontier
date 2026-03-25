export type FrontierNodeTemplate = {
  id: string;
  key: `frontier/${string}`;
  name: string;
  category: "Core" | "Agent" | "Knowledge" | "Integration" | "Control" | "Logic";
  description: string;
  color: string;
};

export const frontierNodeTemplates: FrontierNodeTemplate[] = [
  {
    id: "0f73d594-e1da-4cb4-99cf-d42adf08c701",
    key: "frontier/trigger",
    name: "Trigger",
    category: "Core",
    description: "Workflow entrypoint for user kickoff, schedule, or external event.",
    color: "#6ca0ff",
  },
  {
    id: "5be6c72d-d5b4-49b5-a92f-8c31ccf97e03",
    key: "frontier/agent",
    name: "Agent",
    category: "Agent",
    description: "Execute a delegated objective with a selected specialist agent.",
    color: "#1f7f53",
  },
  {
    id: "32d0f4db-6f9a-4a49-b4f6-3ac950d0a20f",
    key: "frontier/prompt",
    name: "Prompt",
    category: "Agent",
    description: "Compose reusable system prompt instructions and pass them to agent nodes.",
    color: "#5f4bb6",
  },
  {
    id: "6ada404d-6f84-4eca-a8b9-4f4fd272f9e8",
    key: "frontier/tool-call",
    name: "Tool / API Call",
    category: "Integration",
    description: "Invoke external APIs or internal tools with schema-validated IO.",
    color: "#6fd3ff",
  },
  {
    id: "8f76f2e9-8bf3-4ec7-b84b-09d877f3ac67",
    key: "frontier/retrieval",
    name: "Retrieval",
    category: "Knowledge",
    description: "Retrieve and rank context from vector DB, docs, or KB sources.",
    color: "#8a6717",
  },
  {
    id: "9e2c1f8e-4108-4f0c-955a-f4852197a20b",
    key: "frontier/memory",
    name: "Memory",
    category: "Knowledge",
    description: "Read/write short-term or long-term memory scoped to tenant/run.",
    color: "#4f5966",
  },
  {
    id: "a2f7e5e0-53e8-466d-9424-f24f7662f66a",
    key: "frontier/guardrail",
    name: "Guardrail",
    category: "Control",
    description: "Apply safety, policy, and quality controls to input/output content.",
    color: "#9f3550",
  },
  {
    id: "b4df152e-2fb5-4f08-b7c8-c8be8c66ef04",
    key: "frontier/human-review",
    name: "Human Review",
    category: "Control",
    description: "Approval or clarification gate with feedback loop and audit trail.",
    color: "#8d5c1a",
  },
  {
    id: "ce081f92-13ee-4484-8619-8e67b9fcf1a5",
    key: "frontier/output",
    name: "Output",
    category: "Core",
    description: "Finalize artifacts, emit events, and publish run outcomes.",
    color: "#69a3ff",
  },
  {
    id: "2f8c4a4e-80a2-4c4b-a84e-aab3774af8f2",
    key: "frontier/manifold",
    name: "Manifold",
    category: "Logic",
    description: "Consolidate multiple inbound events/flows with AND/OR logic into a single output.",
    color: "#7863d3",
  },
];

export const frontierCanvasNodes = frontierNodeTemplates.map((template) => ({
  key: template.key,
  type: template.key.replace("frontier/", ""),
  title: template.name,
  color: template.color,
  description: template.description,
}));
