import { Badge } from "@/components/ui/Badge";
import type { EvidenceItem } from "@/lib/api";

export function EvidencePanel({ evidence }: { evidence: EvidenceItem[] }) {
  if (evidence.length === 0) return null;

  return (
    <details className="rounded-control border border-ink-100 bg-ink-50 p-3 text-sm transition-colors hover:border-ink-200">
      <summary className="focus-ring cursor-pointer select-none font-medium text-brand-700 transition-colors hover:text-brand-800">
        Why am I seeing this answer?
      </summary>
      <div className="animate-fade-in mt-3 flex flex-col gap-2 text-ink-500">
        <p>
          ✓ Retrieved from {evidence.length} reference {evidence.length === 1 ? "passage" : "passages"} &nbsp;
          ✓ Unsupported claims filtered before showing this answer
        </p>
        <ul className="flex flex-col gap-2">
          {evidence.map((item, i) => (
            <li key={i} className="rounded-control bg-white p-3 transition-shadow hover:shadow-card">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <Badge tone="brand">{item.source_name}</Badge>
                <span className="font-medium text-ink-800">{item.document_title}</span>
              </div>
              <p className="text-ink-500">{item.snippet}</p>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="focus-ring text-brand-700 underline decoration-transparent underline-offset-2 transition-colors hover:decoration-brand-700"
                >
                  View source
                </a>
              )}
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
