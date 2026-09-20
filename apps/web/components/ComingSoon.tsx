import { EkgLine } from "@/components/EkgLine";
import { LogoMark } from "@/components/Logo";
import { LinkButton } from "@/components/ui/Button";

const FLOATING_ICONS = ["💊", "🩺", "📄", "❤️", "🔬", "🧬"];

export function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div className="relative flex min-h-[65vh] flex-col items-center justify-center overflow-hidden rounded-card border border-ink-100 bg-white px-6 py-16 text-center">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="animate-blob absolute -left-16 -top-16 h-72 w-72 rounded-full bg-brand-200 opacity-40 blur-3xl" />
        <div
          className="animate-blob absolute -right-16 top-1/3 h-72 w-72 rounded-full bg-brand-300 opacity-30 blur-3xl"
          style={{ animationDelay: "2s" }}
        />
        <div
          className="animate-blob absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-urgent-100 opacity-30 blur-3xl"
          style={{ animationDelay: "4s" }}
        />
      </div>

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {FLOATING_ICONS.map((icon, i) => (
          <span
            key={icon}
            className="animate-float-up absolute bottom-0 text-3xl opacity-0"
            style={{ left: `${8 + i * 15}%`, animationDelay: `${i * 1.1}s` }}
            aria-hidden="true"
          >
            {icon}
          </span>
        ))}
      </div>

      <EkgLine className="absolute inset-x-0 top-1/2 h-16 -translate-y-1/2 text-brand-100" strokeWidth={4} />

      <div className="relative z-10 flex flex-col items-center gap-4">
        <LogoMark className="h-16 w-16 animate-heartbeat drop-shadow-lg" />
        <span className="animate-shimmer inline-block bg-gradient-to-r from-brand-600 via-brand-300 to-brand-600 bg-clip-text pb-2 text-4xl font-bold leading-[1.3] text-transparent">
          Coming Soon
        </span>
        <h1 className="text-xl font-semibold text-ink-900">{title}</h1>
        <p className="max-w-md text-sm text-ink-500">{description}</p>
        <LinkButton href="/chat" className="mt-2">
          Try MediAssist instead
        </LinkButton>
      </div>
    </div>
  );
}
