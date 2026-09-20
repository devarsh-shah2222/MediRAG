"use client";

import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiError, listRagDocuments, listRagSources, reindexRag } from "@/lib/api";

export default function AdminPage() {
  const [sources, setSources] = useState<any[] | null>(null);
  const [documents, setDocuments] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMessage, setReindexMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [s, d] = await Promise.all([listRagSources(), listRagDocuments()]);
      setSources(s);
      setDocuments(d);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError("Please log in as an admin to view this page.");
      else if (err instanceof ApiError && err.status === 403) setError("Admin access is required to view this page.");
      else setError("Couldn't load the source registry right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleReindex() {
    setReindexing(true);
    setReindexMessage(null);
    try {
      const result = await reindexRag();
      setReindexMessage(`Re-indexed ${result.reindexed_chunks} chunks.`);
    } catch {
      setReindexMessage("Re-index failed. Please try again.");
    } finally {
      setReindexing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) return <Alert tone="urgent">{error}</Alert>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink-900">RAG source registry</h1>
        <Button variant="secondary" onClick={handleReindex} disabled={reindexing}>
          {reindexing ? "Re-indexing..." : "Re-index all chunks"}
        </Button>
      </div>
      {reindexMessage && <Alert tone="success">{reindexMessage}</Alert>}

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-ink-900">Sources ({sources?.length ?? 0})</h2>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-ink-100 text-ink-500">
              <th className="py-2">Name</th>
              <th className="py-2">Type</th>
              <th className="py-2">Jurisdiction</th>
              <th className="py-2">Last ingested</th>
            </tr>
          </thead>
          <tbody>
            {sources?.map((s) => (
              <tr key={s.id} className="border-b border-ink-50">
                <td className="py-2">{s.name}</td>
                <td className="py-2">{s.source_type}</td>
                <td className="py-2">{s.jurisdiction}</td>
                <td className="py-2">{s.last_ingested_at ? new Date(s.last_ingested_at).toLocaleString() : "Never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-ink-900">Documents ({documents?.length ?? 0})</h2>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-ink-100 text-ink-500">
              <th className="py-2">Title</th>
              <th className="py-2">Topic</th>
              <th className="py-2">Version</th>
              <th className="py-2">Chunks</th>
              <th className="py-2">Demo?</th>
            </tr>
          </thead>
          <tbody>
            {documents?.map((d) => (
              <tr key={d.id} className="border-b border-ink-50">
                <td className="py-2">{d.title}</td>
                <td className="py-2">{d.medical_topic}</td>
                <td className="py-2">{d.content_version}</td>
                <td className="py-2">{d.chunk_count}</td>
                <td className="py-2">{d.is_demo ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
