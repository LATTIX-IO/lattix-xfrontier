import { getAgentDefinition, getAgentDefinitions } from "@/lib/api";
import { AgentStudioClient } from "./page.client";

export default async function AgentStudioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: agentId } = await params;
  const agents = await getAgentDefinitions();
  const listedAgent = agents.find((agent) => agent.id === agentId);
  const selectedAgent = await getAgentDefinition(agentId);
  const agentName = selectedAgent?.name || listedAgent?.name || "Agent";
  const initialGraph = selectedAgent?.config_json?.graph_json;

  return <AgentStudioClient agentId={agentId} agentName={agentName} initialGraph={initialGraph} />;
}
