type Tone = "neutral" | "brand" | "urgent" | "emergency";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-ink-100 text-ink-700",
  brand: "bg-brand-100 text-brand-700",
  urgent: "bg-urgent-100 text-urgent-700",
  emergency: "bg-emergency-100 text-emergency-700 animate-pulse",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-sm font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  );
}
