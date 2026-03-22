import { getArtifacts } from "@/lib/api";

export default async function ArtifactsPage() {
  const artifacts = await getArtifacts();

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Artifacts Library</h1>
        <p className="fx-muted">Searchable outputs with versioning, approvals, and guardrail status.</p>
      </header>

      <div className="fx-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Artifact</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Version</th>
              <th className="px-3 py-2 text-left">History</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => (
              <tr key={artifact.id} className="border-t border-[var(--fx-border)]">
                <td className="px-3 py-2 text-[var(--foreground)]">{artifact.name}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">{artifact.status}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">v{artifact.version}</td>
                <td className="fx-muted px-3 py-2">Version diff + approval timeline</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
