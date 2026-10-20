import { cx } from "./ui";

/** The specimen mark: a framed patch grid with one cell lit, the detector's view in miniature. */
export function SpecimenGlyph({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 22 22" className={cx("shrink-0", className ?? "size-[22px]")}>
      <rect x="0.75" y="0.75" width="20.5" height="20.5" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <g fill="currentColor" opacity="0.35">
        <rect x="4.5" y="4.5" width="3.5" height="3.5" />
        <rect x="9.25" y="4.5" width="3.5" height="3.5" />
        <rect x="14" y="4.5" width="3.5" height="3.5" />
        <rect x="4.5" y="9.25" width="3.5" height="3.5" />
        <rect x="9.25" y="9.25" width="3.5" height="3.5" />
        <rect x="4.5" y="14" width="3.5" height="3.5" />
        <rect x="9.25" y="14" width="3.5" height="3.5" />
        <rect x="14" y="14" width="3.5" height="3.5" />
      </g>
      <rect x="14" y="9.25" width="3.5" height="3.5" fill="var(--glow)" />
    </svg>
  );
}

/** Glyph and name, as set on the rail and the extension's top bar. */
export function WordmarkLockup({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <SpecimenGlyph className={compact ? "size-5" : undefined} />
      <span className={cx("font-extrabold tracking-[-0.015em]", compact ? "text-[18px] leading-6" : "text-[20px] leading-7")}>WildcatVerify</span>
    </span>
  );
}
