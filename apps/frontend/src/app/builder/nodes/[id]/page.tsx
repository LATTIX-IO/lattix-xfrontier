import Link from "next/link";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function NodeDefinitionPage({ params }: Props) {
  const { id } = await params;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Node Definition</h1>
        <p className="fx-muted">Node detail endpoint addressed by UUID.</p>
      </header>

      <div className="fx-panel space-y-3 p-4">
        <p className="font-mono text-xs text-[var(--foreground)]">node_id: {id}</p>
        <p className="fx-muted text-sm">
          Use this UUID route to reference node templates, revisions, and customization presets without relying on mutable node names.
        </p>
        <Link href="/builder/nodes" className="fx-btn-secondary inline-flex px-3 py-2 text-sm">
          Back to node catalog
        </Link>
      </div>
    </section>
  );
}
