"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addKnowledgeDocument,
  createKnowledgeCollection,
  deleteKnowledgeCollection,
  getKnowledgeCollections,
  searchKnowledgeCollection,
  type KnowledgeCollection,
  type KnowledgeSearchResult,
} from "@/lib/api";

export default function KnowledgePage() {
  const [collections, setCollections] = useState<KnowledgeCollection[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [docName, setDocName] = useState("");
  const [docText, setDocText] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);

  const refresh = useCallback(async () => {
    try {
      const data = await getKnowledgeCollections();
      setCollections(data);
      setSelected((current) => current ?? data[0]?.id ?? null);
      setError(null);
    } catch {
      setError("Unable to load knowledge collections.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const active = collections.find((c) => c.id === selected) ?? null;

  async function addCollection() {
    if (!newName.trim()) {
      setNotice("Collection name is required.");
      return;
    }
    setBusy(true);
    try {
      const created = await createKnowledgeCollection(newName.trim(), newDescription.trim());
      setNewName("");
      setNewDescription("");
      setSelected(created.id);
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to create collection.");
    } finally {
      setBusy(false);
    }
  }

  async function ingestDocument() {
    if (!active || !docText.trim()) {
      setNotice("Select a collection and paste document text first.");
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const result = await addKnowledgeDocument(active.id, docName.trim() || "document", docText);
      setNotice(`Indexed ${result.chunks_indexed} chunk(s) from "${docName || "document"}".`);
      setDocName("");
      setDocText("");
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to ingest document.");
    } finally {
      setBusy(false);
    }
  }

  async function runSearch() {
    if (!active || !query.trim()) {
      return;
    }
    setBusy(true);
    setNotice(null);
    setResults([]);
    try {
      const response = await searchKnowledgeCollection(active.id, query.trim());
      setResults(response.results);
      if (response.results.length === 0) {
        setNotice(response.reason ? `No results — ${response.reason}.` : "No matching chunks found.");
      }
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Knowledge</h1>
        <p className="fx-muted">
          Document collections chunked and embedded into the platform&apos;s vector store for retrieval and
          citation. Reuses the long-term memory backend (Postgres + embeddings).
        </p>
      </header>

      {error ? <div className="fx-panel border-[hsl(var(--state-critical)/0.4)] p-3 text-sm">{error}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <aside className="space-y-3">
          <article className="fx-panel p-3">
            <h2 className="mb-2 text-sm font-semibold">Collections</h2>
            <ul className="space-y-1 text-sm">
              {collections.map((collection) => (
                <li key={collection.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(collection.id)}
                    className={`w-full rounded border px-2 py-1.5 text-left ${
                      collection.id === selected
                        ? "border-[hsl(var(--accent)/0.5)] bg-[hsl(var(--accent)/0.1)]"
                        : "border-[var(--fx-border)] bg-[var(--fx-surface-elevated)]"
                    }`}
                  >
                    <span className="font-medium text-[var(--foreground)]">{collection.name}</span>
                    <span className="fx-muted block text-xs">
                      {collection.document_count} doc(s) · {collection.chunk_count} chunk(s)
                    </span>
                  </button>
                </li>
              ))}
              {collections.length === 0 ? (
                <li className="fx-muted text-xs">No collections yet.</li>
              ) : null}
            </ul>
          </article>

          <article className="fx-panel space-y-2 p-3 text-xs">
            <h2 className="text-sm font-semibold">New collection</h2>
            <input
              className="fx-field h-8 w-full px-2"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Collection name"
            />
            <input
              className="fx-field h-8 w-full px-2"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              placeholder="Description (optional)"
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => void addCollection()}
              className="fx-btn-primary w-full px-3 py-1.5 font-medium disabled:opacity-60"
            >
              Create collection
            </button>
          </article>
        </aside>

        <div className="space-y-4">
          {active ? (
            <>
              <article className="fx-panel p-3 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-sm font-semibold">{active.name}</h2>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        await deleteKnowledgeCollection(active.id);
                        setSelected(null);
                        await refresh();
                      } catch {
                        setNotice("Unable to delete collection.");
                      }
                    }}
                    className="fx-btn-secondary px-2 py-1 text-[11px]"
                  >
                    Delete collection
                  </button>
                </div>
                <p className="fx-muted mt-1">{active.description || "No description."}</p>
              </article>

              <article className="fx-panel space-y-2 p-3 text-xs">
                <h2 className="text-sm font-semibold">Add document</h2>
                <input
                  className="fx-field h-8 w-full px-2"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                  placeholder="Document name"
                />
                <textarea
                  className="fx-field min-h-32 w-full p-2"
                  value={docText}
                  onChange={(e) => setDocText(e.target.value)}
                  placeholder="Paste document text — it will be chunked and embedded."
                />
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void ingestDocument()}
                  className="fx-btn-primary px-3 py-1.5 font-medium disabled:opacity-60"
                >
                  Index document
                </button>
              </article>

              <article className="fx-panel space-y-2 p-3 text-xs">
                <h2 className="text-sm font-semibold">Test retrieval</h2>
                <div className="flex gap-2">
                  <input
                    className="fx-field h-8 flex-1 px-2"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void runSearch();
                    }}
                    placeholder="Search query..."
                  />
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void runSearch()}
                    className="fx-btn-secondary px-3 py-1.5 font-medium disabled:opacity-60"
                  >
                    Search
                  </button>
                </div>
                {results.length > 0 ? (
                  <ul className="space-y-2">
                    {results.map((result, index) => (
                      <li key={index} className="rounded border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
                        <div className="mb-1 flex items-center justify-between gap-2 text-[10px] uppercase tracking-wide fx-muted">
                          <span>{result.document_name || "document"} · chunk {result.chunk_index}</span>
                          {typeof result.score === "number" ? <span>score {result.score.toFixed(3)}</span> : null}
                        </div>
                        <p className="whitespace-pre-wrap text-[var(--foreground)]">{result.content}</p>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            </>
          ) : (
            <article className="fx-panel p-4 text-sm fx-muted">
              Select or create a collection to add documents and test retrieval.
            </article>
          )}
        </div>
      </div>

      {notice ? <p className="fx-muted text-xs">{notice}</p> : null}
    </section>
  );
}
