import { notFound } from "next/navigation";
import { WorkflowPipelineDetail } from "@/components/workflow-pipeline";
import { getPublishedWorkflows } from "@/lib/api";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function WorkflowDetailPage({ params }: Props) {
  const { id } = await params;
  const workflows = await getPublishedWorkflows();
  const workflow = workflows.find((item) => item.id === id);

  if (!workflow) {
    notFound();
  }

  return <WorkflowPipelineDetail workflow={workflow} />;
}
