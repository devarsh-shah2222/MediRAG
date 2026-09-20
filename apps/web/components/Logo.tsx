export function LogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3fbcae" />
          <stop offset="1" stopColor="#146560" />
        </linearGradient>
        <radialGradient id="logo-gloss" cx="35%" cy="22%" r="65%">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.4" />
          <stop offset="60%" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="32" cy="32" r="30" fill="url(#logo-g)" />
      <circle cx="32" cy="32" r="30" fill="url(#logo-gloss)" />
      <circle cx="32" cy="32" r="29.25" fill="none" stroke="#0f3d3a" strokeOpacity="0.18" strokeWidth="1.5" />
      <rect x="27" y="14" width="10" height="36" rx="4" fill="#ffffff" />
      <rect x="14" y="27" width="36" height="10" rx="4" fill="#ffffff" />
      <path
        d="M10 32 H21 L25 21 L31 43 L35 25 L39 32 H54"
        fill="none"
        stroke="#0f3d3a"
        strokeOpacity="0.85"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Logo({ wordmark, className = "" }: { wordmark: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark className="h-8 w-8 shrink-0 drop-shadow-sm transition-transform duration-200 ease-out group-hover:scale-105" />
      <span className="text-lg font-semibold text-brand-700">{wordmark}</span>
    </span>
  );
}
