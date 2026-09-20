export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="animate-fade-in flex flex-col items-center gap-3 rounded-card border border-dashed border-ink-200 bg-white p-10 text-center">
      <p className="text-lg font-semibold text-ink-800">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-500">{description}</p>}
      {action}
    </div>
  );
}
