import { LinkButton } from "@/components/ui/Button";
import type { ChatAction } from "@/lib/api";

export function EmergencyBanner({
  answer,
  actions,
  contacts,
}: {
  answer: string;
  actions: ChatAction[];
  contacts?: { emergency_number: string | null; poison_control: string | null; note?: string } | null;
}) {
  return (
    <div role="alert" className="animate-fade-up flex flex-col gap-4 rounded-card border-2 border-emergency-600 bg-emergency-50 p-6">
      <p className="text-xl font-bold text-emergency-700">Urgent medical attention may be needed</p>
      <p className="text-base text-emergency-700">{answer}</p>

      <div className="flex flex-col gap-3 sm:flex-row">
        {actions.map((action) =>
          action.type === "navigate" && action.target ? (
            <LinkButton key={action.id} variant="emergency" className="w-full sm:w-auto" href={action.target}>
              {action.label}
            </LinkButton>
          ) : (
            <LinkButton
              key={action.id}
              variant="emergency"
              className="w-full sm:w-auto"
              href={contacts?.emergency_number ? `tel:${contacts.emergency_number}` : undefined}
              disabled={!contacts?.emergency_number}
            >
              {contacts?.emergency_number ? `${action.label} (${contacts.emergency_number})` : action.label}
            </LinkButton>
          )
        )}
      </div>

      {contacts && !contacts.emergency_number && (
        <p className="text-sm text-emergency-700">{contacts.note}</p>
      )}
    </div>
  );
}
