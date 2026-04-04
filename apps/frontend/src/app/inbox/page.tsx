import { UserChatWorkspace } from "@/components/user-chat-workspace";
import { getInbox, getWorkflowRuns } from "@/lib/api";
type InboxPageProps = {
  searchParams: Promise<{ session?: string; details?: string; tab?: string }>;
};

export default async function InboxPage({ searchParams }: InboxPageProps) {
  const [{ session, details, tab }, items, runs] = await Promise.all([searchParams, getInbox(), getWorkflowRuns()]);

  return (
    <UserChatWorkspace
      initialRuns={runs}
      initialInbox={items}
      initialSelectedRunId={session ?? null}
      initialDetailsOpen={details === "1"}
      initialTab={tab === "graph" ? "graph" : "chat"}
    />
  );
}
