import { AnchorHTMLAttributes, ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "emergency";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 hover:shadow-floating focus-visible:outline-brand-700",
  secondary: "bg-white text-ink-800 border border-ink-200 hover:bg-ink-50 hover:border-ink-300",
  ghost: "bg-transparent text-brand-700 hover:bg-brand-50",
  emergency: "bg-emergency-600 text-white hover:bg-emergency-700 hover:shadow-floating",
};

export function buttonClassName(variant: Variant = "primary", className = ""): string {
  return `focus-ring inline-flex min-h-[44px] items-center justify-center gap-2 rounded-control px-5 py-2.5 text-base font-medium transition-all duration-150 ease-out hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none ${VARIANT_CLASSES[variant]} ${className}`;
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
    </svg>
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className = "", loading = false, disabled, children, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      className={buttonClassName(variant, className)}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
});

interface LinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: Variant;
  disabled?: boolean;
}

/** An <a> styled like a Button. Use this instead of nesting a <button> inside
 * an <a> (invalid, and confusing for screen readers/keyboard nav). */
export const LinkButton = forwardRef<HTMLAnchorElement, LinkButtonProps>(function LinkButton(
  { variant = "primary", className = "", disabled, href, onClick, ...props },
  ref
) {
  return (
    <a
      ref={ref}
      href={disabled ? undefined : href}
      aria-disabled={disabled || undefined}
      role={!href || disabled ? "button" : undefined}
      tabIndex={disabled ? -1 : undefined}
      onClick={disabled ? (e) => e.preventDefault() : onClick}
      className={buttonClassName(variant, className)}
      {...props}
    />
  );
});
