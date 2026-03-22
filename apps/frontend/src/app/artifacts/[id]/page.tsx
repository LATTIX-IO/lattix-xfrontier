import { getArtifact } from "@/lib/api";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function ArtifactDetailPage({ params }: Props) {
  const { id } = await params;
  const artifact = await getArtifact(id);

  if (!artifact) {
    return (
      <section className="space-y-4">
        <header>
          <h1 className="text-2xl font-semibold">Artifact not found</h1>
          <p className="fx-muted">We couldn&apos;t find artifact <span className="font-mono">{id}</span>.</p>
        </header>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">{artifact.name}</h1>
        <p className="fx-muted text-sm">
          Status: {artifact.status} • Version: v{artifact.version} • Created: {artifact.createdAt}
        </p>
        <p className="fx-muted text-xs">
          Artifact ID: <span className="font-mono">{artifact.id}</span>
          {artifact.run_id ? (
            <>
              {" "}• Run ID: <span className="font-mono">{artifact.run_id}</span>
            </>
          ) : null}
        </p>
      </header>

      <article className="fx-panel p-3">
        <h2 className="mb-2 text-sm font-semibold">Content</h2>
        <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-3 text-xs text-[var(--foreground)]">
          {artifact.content}
        </pre>
      </article>
    </section>
  );
}
