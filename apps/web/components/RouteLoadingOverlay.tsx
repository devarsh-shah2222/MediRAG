"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { EkgLine } from "@/components/EkgLine";
import { LogoMark } from "@/components/Logo";

const MIN_VISIBLE_MS = 400;
const SAFETY_TIMEOUT_MS = 4000;

/** Shows a heartbeat-pulsing logo overlay while an internal <Link> navigation
 * is in flight, since App Router client components render near-instantly and
 * otherwise give no feedback that a tab switch registered. Also covers a full
 * page load/refresh: `loading` starts true (matching the server-rendered HTML,
 * so there's no hydration mismatch), and clears once the browser actually
 * finishes loading the page. */
export function RouteLoadingOverlay() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(true);
  const shownAtRef = useRef(Date.now());
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const safetyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const skipNextPathnameHideRef = useRef(true);

  useEffect(() => {
    function finishInitialLoad() {
      const elapsed = Date.now() - shownAtRef.current;
      hideTimerRef.current = setTimeout(() => setLoading(false), Math.max(MIN_VISIBLE_MS - elapsed, 0));
    }
    safetyTimerRef.current = setTimeout(() => setLoading(false), SAFETY_TIMEOUT_MS);
    if (document.readyState === "complete") {
      finishInitialLoad();
    } else {
      window.addEventListener("load", finishInitialLoad, { once: true });
      return () => window.removeEventListener("load", finishInitialLoad);
    }
    // Runs once for the initial page load only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      // Note: e.defaultPrevented is NOT a useful guard here -- Next.js's <Link>
      // always calls preventDefault() to do client-side routing, so a normal
      // navigation click already has it set to true by the time this (later,
      // document-level) listener runs.
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = (e.target as HTMLElement).closest("a");
      if (!link || link.getAttribute("aria-disabled") === "true") return;
      const href = link.getAttribute("href");
      if (!href || !href.startsWith("/") || (link.target && link.target !== "_self")) return;
      if (href === pathname) return;

      shownAtRef.current = Date.now();
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current);
      safetyTimerRef.current = setTimeout(() => setLoading(false), SAFETY_TIMEOUT_MS);
      setLoading(true);
    }

    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [pathname]);

  useEffect(() => {
    // The initial-mount run of this effect corresponds to the page-load case
    // above (handled by its own load/readyState logic), not a click-triggered
    // navigation landing -- skip it so the two hide strategies don't race.
    if (skipNextPathnameHideRef.current) {
      skipNextPathnameHideRef.current = false;
      return;
    }
    if (!loading) return;
    const elapsed = Date.now() - shownAtRef.current;
    hideTimerRef.current = setTimeout(() => setLoading(false), Math.max(MIN_VISIBLE_MS - elapsed, 0));
    if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current);
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
    // Only the pathname change (navigation landing) should decide when to hide.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  if (!loading) return null;

  return (
    <div className="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-white/70 backdrop-blur-sm">
      <EkgLine className="absolute inset-x-0 top-1/2 h-20 -translate-y-1/2 text-brand-400/60" strokeWidth={4} />
      <LogoMark className="relative z-10 h-20 w-20 animate-heartbeat drop-shadow-lg" />
    </div>
  );
}
