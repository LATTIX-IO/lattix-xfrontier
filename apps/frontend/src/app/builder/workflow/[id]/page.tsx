import { redirect } from "next/navigation";

export default async function WorkflowAliasPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/builder/workflows/${id}`);
}
