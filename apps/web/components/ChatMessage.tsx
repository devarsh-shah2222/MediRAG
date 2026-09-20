import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EkgLine } from "@/components/EkgLine";
import { EmergencyBanner } from "@/components/EmergencyBanner";
import { EvidencePanel } from "@/components/EvidencePanel";
import type { ChatResponse } from "@/lib/api";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

export function ThinkingBubble({ label = "Thinking..." }: { label?: string }) {
  return (
    <div className="animate-fade-up flex justify-start" role="status" aria-live="polite" aria-label={label}>
      <div className="flex items-center gap-3 rounded-card rounded-bl-sm bg-white px-4 py-3.5 shadow-card">
        <EkgLine className="h-5 w-14 text-brand-400" strokeWidth={4} />
        <span className="text-sm text-ink-500">{label}</span>
      </div>
    </div>
  );
}

export function ChatMessage({
  message,
  onAction,
}: {
  message: DisplayMessage;
  onAction: (actionId: string, target?: string | null) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="animate-fade-up flex justify-end">
        <p className="max-w-[85%] rounded-card rounded-br-sm bg-brand-600 px-4 py-3 text-white">{message.content}</p>
      </div>
    );
  }

  const response = message.response;

  if (response?.mode === "emergency_navigation") {
    return <EmergencyBanner answer={response.answer} actions={response.actions} contacts={response.emergency_contacts} />;
  }

  return (
    <div className="animate-fade-up flex flex-col gap-3">
      <div
        className={`max-w-[85%] rounded-card rounded-bl-sm px-4 py-3 transition-shadow ${response?.mode === "urgent" ? "border border-urgent-500 bg-urgent-50" : "bg-white shadow-card"}`}
      >
        {response?.mode === "urgent" && <Badge tone="urgent">May need prompt attention</Badge>}
        <p className="mt-1 whitespace-pre-wrap text-ink-900">{message.content}</p>
      </div>

      {response && response.evidence.length > 0 && <EvidencePanel evidence={response.evidence} />}

      {response && response.actions.filter((a) => a.type !== "toggle_evidence" && a.id !== "explain_simpler").length > 0 && (
        <div className="flex flex-wrap gap-2">
          {response.actions
            .filter((a) => a.type !== "toggle_evidence" && a.id !== "explain_simpler")
            .map((action) => (
              <Button key={action.id} variant="secondary" onClick={() => onAction(action.id, action.target)}>
                {action.label}
              </Button>
            ))}
        </div>
      )}

      {response && <p className="text-xs text-ink-500">{response.disclaimer}</p>}
    </div>
  );
}
