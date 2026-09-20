const UNIT_WIDTH = 200;
const UNITS = 16;
const BASELINE = 50;
const AMPLITUDE = 42;

function buildPath(): string {
  let d = `M0,${BASELINE}`;
  for (let i = 0; i < UNITS; i++) {
    const x0 = i * UNIT_WIDTH;
    d += ` L${x0 + 70},${BASELINE}`;
    d += ` L${x0 + 82},${BASELINE + 15}`;
    d += ` L${x0 + 94},${BASELINE - AMPLITUDE}`;
    d += ` L${x0 + 106},${BASELINE + AMPLITUDE}`;
    d += ` L${x0 + 118},${BASELINE}`;
    d += ` L${x0 + UNIT_WIDTH},${BASELINE}`;
  }
  return d;
}

const PATH = buildPath();
const VIEWBOX_WIDTH = UNIT_WIDTH * UNITS;

/** A continuously-looping EKG/heartbeat trace. `className` sizes and colors
 * the (overflow-hidden) viewport -- the line itself is drawn twice as wide
 * and scrolled left-to-right, looping seamlessly since every unit is identical. */
export function EkgLine({ className = "", strokeWidth = 3 }: { className?: string; strokeWidth?: number }) {
  return (
    <div className={`overflow-hidden ${className}`}>
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} 100`}
        preserveAspectRatio="none"
        className="animate-ekg-scroll h-full w-[200%]"
        aria-hidden="true"
      >
        <path d={PATH} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
