type Tone = "info" | "urgent" | "emergency" | "success";

const TONE_CLASSES: Record<Tone, string> = {
  info: "bg-brand-50 border-brand-200 text-brand-800",
  urgent: "bg-urgent-50 border-urgent-500 text-urgent-700",
  emergency: "bg-emergency-50 border-emergency-600 text-emergency-700",
  success: "bg-brand-50 border-brand-300 text-brand-800",
};

export function Alert({
  tone = "info",
  title,
  children,
}: {
  tone?: Tone;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div role={tone === "emergency" ? "alert" : "status"} className={`rounded-card border-l-4 p-4 ${TONE_CLASSES[tone]}`}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  );
}
