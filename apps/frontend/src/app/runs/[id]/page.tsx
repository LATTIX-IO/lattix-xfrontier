import { RunConversationConsole } from "@/components/run-conversation-console";
import { getWorkflowRun, getWorkflowRunEvents } from "@/lib/api";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function RunConversationPage({ params }: Props) {
  const { id } = await params;
  const [run, events] = await Promise.all([getWorkflowRun(id), getWorkflowRunEvents(id)]);
  return <RunConversationConsole runId={id} run={run} events={events} />;
}
