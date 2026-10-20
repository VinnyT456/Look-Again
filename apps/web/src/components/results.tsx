"use client";

import { Check, FlaskConical, RotateCcw, Share } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";

import {
  cellPlace,
  HEATMAP_GRID,
  heatmapCoveredRegion,
  heatmapHasSignal,
  heatmapIntensities,
  heatmapPeaks,
  type PatchHeatmap,
} from "@/lib/models/classification";
import { hasAnomaly, verdictLabel } from "@/lib/models/verdict";
import { BROWSING_TITLE, shareText, timeAgo, type VerificationCase } from "@/lib/models/verification-case";

import { verdictTone } from "./icons";
import { Button, cx, Ruled, SectionTitle, Segmented, Spinner, VerdictMark } from "./ui";

type Light = "plain" | "detector";
const lights = ["plain", "detector"] as const;

/** A numbered place on the photo, in fractions of the image. */
interface Mark {
  place: string;
  detail: string;
  /** Null until the photo's size is known, for heatmap peaks. */
  at: { x: number; y: number } | null;
}

const rankDetail = ["Strongest influence", "Second strongest", "Third strongest"];
const pinSize = ["size-10 text-body", "size-[34px] text-body", "size-7 text-small"];

/** Where the detector looked: heatmap peaks for detector results, the flagged area for demo ones. */
function marksFor(item: VerificationCase, showsHeatmap: boolean, size: { width: number; height: number } | null): Mark[] {
  if (showsHeatmap && item.heatmap) {
    const region = size ? heatmapCoveredRegion(size.width, size.height) : null;
    return heatmapPeaks(item.heatmap).map((peak, rank) => ({
      place: cellPlace(peak.row, peak.column),
      detail: rankDetail[rank],
      at: region && {
        x: region.x + ((peak.column + 0.5) / HEATMAP_GRID) * region.width,
        y: region.y + ((peak.row + 0.5) / HEATMAP_GRID) * region.height,
      },
    }));
  }
  if (item.hotspot && hasAnomaly(item.verdict)) {
    const { xRatio, yRatio, widthRatio, heightRatio, label } = item.hotspot;
    return [{ place: label, detail: "Flagged area", at: { x: xRatio + widthRatio / 2, y: yRatio + heightRatio / 2 } }];
  }
  return [];
}

/**
 * The verdict for one image as a condition report: the photo on the bench
 * (left), and the object label with its notes (right). The halves stack in
 * narrow containers such as the extension's side panel.
 *
 * `onCheckAnother` hides "Check another" when absent; `inShareSheet`
 * (the browser extension) hides "Open on Bluesky", like the mobile share sheets.
 */
export function ResultsView({
  item,
  imageSrc,
  showHeatmap,
  onCheckAnother,
  inShareSheet = false,
}: {
  item: VerificationCase;
  /** What an `<img>` can load for the case's image, or null when it's gone. */
  imageSrc: string | null;
  showHeatmap: boolean;
  onCheckAnother?: () => void;
  inShareSheet?: boolean;
}) {
  const [light, setLight] = useState<Light>("plain");
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const [focused, setFocused] = useState<number | null>(null);
  const bench = useRef<HTMLDivElement>(null);
  const pins = useRef<(HTMLElement | null)[]>([]);
  const notes = useRef<(HTMLElement | null)[]>([]);

  const hasPhoto = item.imageUrl !== null;
  // Only when it backs an AI verdict; on a Real verdict the same map would just be noise.
  const showsHeatmap = showHeatmap && hasPhoto && item.verdict === "ai" && !!item.heatmap && heatmapHasSignal(item.heatmap);
  const marks = hasPhoto ? marksFor(item, showsHeatmap, size) : [];
  // The switch only appears when detector light says something true.
  const canSwitch = hasPhoto && (marks.length > 0 || item.verdict === "real" || showsHeatmap);
  const shownLight = canSwitch ? light : "plain";
  const line = useLeaderLine(bench, notes, pins, shownLight === "detector" ? focused : null);

  return (
    <div className="@container">
      <div ref={bench} className={cx("relative grid overflow-hidden rounded-[3px] border border-rule bg-label", hasPhoto && "@3xl:grid-cols-2")}>
        {hasPhoto && (
          <div className="flex flex-col gap-4 border-b border-rule bg-well p-4 @3xl:border-r @3xl:border-b-0 @3xl:p-6">
            {canSwitch && <Segmented ariaLabel="Light" options={lights} value={light} label={(option) => (option === "plain" ? "Plain light" : "Detector light")} onChange={setLight} className="self-start" />}
            <ResultPhoto
              item={item}
              src={imageSrc}
              light={shownLight}
              showsHeatmap={showsHeatmap}
              marks={marks}
              pins={pins}
              focused={focused}
              onSize={setSize}
            />
            {shownLight === "detector" && (
              <p className="max-w-[60ch] text-small text-muted">
                {showsHeatmap
                  ? "Glowing cells pushed the detector toward AI; numbers mark the strongest areas, largest first. They show influence, not proof."
                  : marks.length > 0
                    ? "The mark shows the area behind this demo verdict."
                    : "The detector found no area that pushed it toward AI."}
              </p>
            )}
          </div>
        )}

        <ObjectLabel item={item} marks={marks} notes={notes} onFocusMark={setFocused} onShowMark={(index) => (setLight("detector"), setFocused(index))} inShareSheet={inShareSheet} onCheckAnother={onCheckAnother} />

        {line && (
          <svg aria-hidden className="pointer-events-none absolute inset-0 size-full overflow-visible">
            <line {...line} stroke="var(--glow)" strokeWidth={1} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
            <circle cx={line.x2} cy={line.y2} r={3} fill="var(--glow)" />
          </svg>
        )}
      </div>
    </div>
  );
}

/** A 1px line from a note's number to its mark on the photo, re-measured from layout whenever either moves. */
function useLeaderLine(
  container: RefObject<HTMLElement | null>,
  from: RefObject<(HTMLElement | null)[]>,
  to: RefObject<(HTMLElement | null)[]>,
  index: number | null,
) {
  const [line, setLine] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);
  useLayoutEffect(() => {
    const box = container.current;
    if (index === null || !box) return;
    // The observer also fires once when attached, which draws the first line.
    const draw = () => {
      const origin = box.getBoundingClientRect();
      const a = from.current[index]?.getBoundingClientRect();
      const b = to.current[index]?.getBoundingClientRect();
      if (!a || !b) return setLine(null);
      setLine({
        x1: Math.round(a.left - origin.left) + 0.5,
        y1: Math.round(a.top + a.height / 2 - origin.top) + 0.5,
        x2: Math.round(b.left + b.width / 2 - origin.left) + 0.5,
        y2: Math.round(b.top + b.height / 2 - origin.top) + 0.5,
      });
    };
    const observer = new ResizeObserver(draw);
    observer.observe(box);
    return () => observer.disconnect();
  }, [container, from, to, index]);
  return index === null ? null : line;
}

/** The right half: the verdict set like a museum object label, then the notes. */
function ObjectLabel({
  item,
  marks,
  notes,
  onFocusMark,
  onShowMark,
  inShareSheet,
  onCheckAnother,
}: {
  item: VerificationCase;
  marks: Mark[];
  notes: RefObject<(HTMLElement | null)[]>;
  onFocusMark: (index: number | null) => void;
  onShowMark: (index: number) => void;
  inShareSheet: boolean;
  onCheckAnother?: () => void;
}) {
  const tone = verdictTone[item.verdict];
  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex flex-col gap-4 border-b border-rule p-4 @3xl:p-6">
        <div className="flex flex-wrap justify-between gap-x-4 gap-y-1 text-small text-muted">
          <CheckedAt item={item} />
          <span>{item.isDemo ? "Demo result" : item.postUrl ? "Bluesky post" : item.title === BROWSING_TITLE ? "Photo on Bluesky" : "Uploaded photo"}</span>
        </div>
        <h2 className="flex items-center gap-3.5">
          <VerdictMark verdict={item.verdict} size="lg" />
          <span>
            <span className={cx("block text-title font-extrabold tracking-[-0.015em]", tone.ink)}>{verdictLabel[item.verdict]}</span>
            <span className="block font-semibold tabular-nums">{item.confidencePercentage}% confidence</span>
          </span>
        </h2>
        <DetectorScale item={item} />
      </div>

      <div className="flex flex-col gap-7 p-4 @3xl:p-6">
        <div className="flex flex-col gap-3">
          <p className="max-w-[65ch]">{item.plainSummary}</p>
          {item.caption && <blockquote className="max-w-[65ch] border-l border-rule-strong pl-4 text-muted">&ldquo;{item.caption}&rdquo;</blockquote>}
        </div>

        {item.isDemo && <DemoNotice />}

        {marks.length > 0 && (
          <section className="flex flex-col gap-2" aria-labelledby="looked-title">
            <SectionTitle id="looked-title">Where the detector looked</SectionTitle>
            <Ruled className="border-y border-rule">
              {marks.map((mark, index) => (
                <button
                  key={mark.place + index}
                  type="button"
                  ref={(node) => {
                    notes.current[index] = node;
                  }}
                  onMouseEnter={() => onFocusMark(index)}
                  onMouseLeave={() => onFocusMark(null)}
                  onFocus={() => onFocusMark(index)}
                  onBlur={() => onFocusMark(null)}
                  onClick={() => onShowMark(index)}
                  className="flex w-full items-center gap-3 py-2.5 text-left transition-colors hover:bg-well focus-visible:-outline-offset-2"
                >
                  <span aria-hidden className="grid size-8 shrink-0 place-items-center rounded-full border-[1.5px] border-accent text-small font-semibold text-accent">
                    {index + 1}
                  </span>
                  <span className="flex-1">
                    <span className="block font-semibold">{mark.place}</span>
                    <span className="block text-small text-muted">{mark.detail}</span>
                  </span>
                  <span className="text-small font-semibold text-accent">Show</span>
                </button>
              ))}
            </Ruled>
          </section>
        )}

        {/* Demo results describe what was seen; detector results list things to check, since the model doesn't report specific evidence. */}
        <section className="flex flex-col gap-2" aria-labelledby="findings-title">
          <SectionTitle id="findings-title">{item.isDemo ? "What we noticed" : "Things to check yourself"}</SectionTitle>
          {item.isDemo ? (
            <Ruled className="border-y border-rule">
              {item.keyFindings.map((finding) => (
                <p key={finding} className="flex gap-3 py-2.5">
                  <span aria-hidden className={cx("mt-[9px] size-1.5 shrink-0 rounded-full", tone.solid)} />
                  {finding}
                </p>
              ))}
            </Ruled>
          ) : (
            <Ruled className="border-y border-rule">
              {item.keyFindings.map((finding) => (
                <label key={finding} className="flex items-start gap-3 py-2.5 transition-colors hover:bg-well">
                  <input type="checkbox" className="peer mt-0.5 size-5 shrink-0 accent-accent" />
                  <span className="peer-checked:text-muted peer-checked:line-through peer-checked:decoration-rule-strong">{finding}</span>
                </label>
              ))}
            </Ruled>
          )}
        </section>

        <section className="flex flex-col gap-2" aria-labelledby="todo-title">
          <SectionTitle id="todo-title">What to do</SectionTitle>
          <p className="max-w-[65ch]">{item.suggestedAction}</p>
        </section>

        <SourceRows item={item} inShareSheet={inShareSheet} />

        <div className="flex flex-wrap gap-2">
          <ShareResultButton item={item} />
          {onCheckAnother && (
            <Button variant="secondary" icon={RotateCcw} onClick={onCheckAnother}>
              Check another
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/** Where this photo landed between Real and AI, with the 50% line the detector decides at. */
function DetectorScale({ item }: { item: VerificationCase }) {
  if (item.verdict === "tampered") return null;
  const aiScore = item.verdict === "ai" ? item.confidencePercentage : 100 - item.confidencePercentage;
  return (
    <div aria-hidden className="max-w-[420px]">
      <div className="relative h-1.5 rounded-full bg-rule-strong/45">
        <span className="absolute top-1/2 left-1/2 h-3.5 w-px -translate-y-1/2 bg-ink/60" />
        <span
          className={cx("absolute top-1/2 size-3.5 -translate-1/2 rounded-full border-2 border-label", verdictTone[item.verdict].solid)}
          style={{ left: `${aiScore}%` }}
        />
      </div>
      <div className="mt-1.5 grid grid-cols-3 text-small text-muted">
        <span>Real</span>
        <span className="text-center">AI at 50%</span>
        <span className="text-right">AI</span>
      </div>
    </div>
  );
}

/** An exact time, so a screenshot can be cited; relative for the bundled examples. */
function CheckedAt({ item }: { item: VerificationCase }) {
  if (item.checkedAt === null) return <span>{timeAgo(item)}</span>;
  return (
    <span suppressHydrationWarning>
      Checked {new Date(item.checkedAt).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
    </span>
  );
}

export function DemoNotice() {
  return (
    <p className="flex gap-3 rounded-[3px] border border-rule-strong bg-well px-4 py-3">
      <FlaskConical aria-hidden className="mt-0.5 size-[18px] shrink-0 text-accent" />
      <span>Demo result. This verdict isn&apos;t from the WildcatVerify detection model, so don&apos;t rely on it.</span>
    </p>
  );
}

function SourceRows({ item, inShareSheet }: { item: VerificationCase; inShareSheet: boolean }) {
  return (
    <section className="flex flex-col gap-2" aria-labelledby="source-title">
      <SectionTitle id="source-title">Source</SectionTitle>
      <Ruled className="border-y border-rule">
        {item.authorHandle ? (
          <SourceRow label="Posted by" value={`@${item.authorHandle}`} />
        ) : (
          <SourceRow label="From" value={item.title === BROWSING_TITLE ? "A photo on Bluesky" : inShareSheet ? "Shared image" : "Your photos"} />
        )}
        {item.imageUrl === null && <SourceRow label="Photo" value="Not included" />}
        {item.postUrl && !inShareSheet && (
          <a href={item.postUrl} target="_blank" rel="noreferrer" className="flex min-h-11 items-center font-semibold text-accent underline-offset-4 hover:underline">
            Open on Bluesky
          </a>
        )}
      </Ruled>
    </section>
  );
}

function SourceRow({ label, value }: { label: string; value: string }) {
  return (
    <p className="flex justify-between gap-4 py-2.5">
      <span className="text-muted">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </p>
  );
}

/**
 * The checked photo, shown whole (never cropped, since a crop could hide the
 * very edit being looked for). Plain light leaves it untouched; detector
 * light darkens it toward UV and lights up where the model looked.
 */
function ResultPhoto({
  item,
  src,
  light,
  showsHeatmap,
  marks,
  pins,
  focused,
  onSize,
}: {
  item: VerificationCase;
  src: string | null;
  light: Light;
  showsHeatmap: boolean;
  marks: Mark[];
  pins: RefObject<(HTMLElement | null)[]>;
  focused: number | null;
  onSize: (size: { width: number; height: number }) => void;
}) {
  const [loaded, setLoaded] = useState<{ width: number; height: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const detector = light === "detector";

  if (!src || failed) {
    return (
      <div className="flex min-h-48 flex-col items-start justify-end gap-2 rounded-[3px] border border-dashed border-rule-strong p-5">
        <VerdictMark verdict={item.verdict} />
        <span className="font-semibold">Photo unavailable</span>
        <span className="text-small text-muted">The verdict and notes still stand.</span>
      </div>
    );
  }

  return (
    <div className="flex min-h-48 flex-1 items-center justify-center p-3 @3xl:min-h-[440px]">
      <div className="relative">
        <CropMarks detector={detector} />
        {/* eslint-disable-next-line @next/next/no-img-element -- remote Bluesky CDN images and in-memory uploads */}
        <img
          src={src}
          alt={detector ? "Checked photo under detector light" : "Checked photo"}
          onLoad={(event) => {
            const size = { width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight };
            setLoaded(size);
            onSize(size);
          }}
          onError={() => setFailed(true)}
          // Small photos are enlarged to a readable size; the width alone sets it so the aspect ratio, and the overlays, hold.
          style={loaded && Math.max(loaded.width, loaded.height) < MIN_PHOTO_SIDE ? { width: (loaded.width * MIN_PHOTO_SIDE) / Math.max(loaded.width, loaded.height) } : undefined}
          className={cx(
            "block h-auto max-h-[440px] w-auto max-w-full shadow-[0_1px_2px_rgb(0_0_0/0.12),0_8px_24px_-8px_rgb(0_0_0/0.25)] transition-[filter] duration-500 ease-out-expo @3xl:max-h-[min(640px,calc(100dvh-220px))]",
            detector && "brightness-[0.55] contrast-[1.1] grayscale",
          )}
        />
        {!loaded && (
          <div className="absolute inset-0 grid min-h-40 min-w-40 place-items-center">
            <Spinner />
          </div>
        )}
        <div aria-hidden className={cx("absolute inset-0 bg-uv mix-blend-multiply transition-opacity duration-500 ease-out-expo", detector ? "opacity-80" : "opacity-0")} />
        <div className={cx("absolute inset-0 transition-opacity duration-500 ease-out-expo", detector ? "opacity-100" : "pointer-events-none opacity-0")} aria-hidden={!detector}>
          {showsHeatmap && item.heatmap && loaded && <FluorescentCells heatmap={item.heatmap} width={loaded.width} height={loaded.height} />}
          {!showsHeatmap && item.hotspot && hasAnomaly(item.verdict) && (
            <div
              className="absolute border-2 border-glow"
              style={{
                left: `${item.hotspot.xRatio * 100}%`,
                top: `${item.hotspot.yRatio * 100}%`,
                width: `${item.hotspot.widthRatio * 100}%`,
                height: `${item.hotspot.heightRatio * 100}%`,
              }}
            />
          )}
          {marks.map(
            (mark, index) =>
              mark.at && (
                <span
                  key={mark.place + index}
                  ref={(node) => {
                    pins.current[index] = node;
                  }}
                  role="img"
                  aria-label={`Mark ${index + 1}: ${mark.place}, ${mark.detail.toLowerCase()}`}
                  className={cx(
                    "absolute grid -translate-1/2 place-items-center rounded-full border-[1.5px] border-uv bg-label leading-none font-semibold text-uv transition-shadow dark:text-wall",
                    "dark:border-wall dark:bg-glow",
                    pinSize[index] ?? pinSize[2],
                    focused === index && "shadow-[0_0_0_4px_var(--glow)]",
                  )}
                  style={{ left: `${mark.at.x * 100}%`, top: `${mark.at.y * 100}%` }}
                >
                  {index + 1}
                </span>
              ),
          )}
          {item.verdict === "real" && (
            <span className="absolute bottom-3 left-3 inline-flex items-center gap-2 rounded-md bg-label px-3 py-2 text-small font-semibold text-real">
              <VerdictMark verdict="real" size="sm" />
              No signs of AI generation found
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

const MIN_PHOTO_SIDE = 400;

/** Registration corners around the photo on the bench, the way an object is framed for documentation. */
export function CropMarks({ detector }: { detector: boolean }) {
  const corner = cx("absolute size-3.5 transition-colors duration-500", detector ? "border-glow" : "border-rule-strong");
  return (
    <span aria-hidden className="pointer-events-none absolute -inset-2.5">
      <span className={cx(corner, "top-0 left-0 border-t border-l")} />
      <span className={cx(corner, "top-0 right-0 border-t border-r")} />
      <span className={cx(corner, "bottom-0 left-0 border-b border-l")} />
      <span className={cx(corner, "right-0 bottom-0 border-r border-b")} />
    </span>
  );
}

/** Cells below this share of the strongest one aren't drawn, so noise doesn't light the whole photo. */
const HEATMAP_FLOOR = 0.2;

/** The detector's 24×24 patch map over the part of the image it saw, one crisp fluorescent cell per patch. */
function FluorescentCells({ heatmap, width, height }: { heatmap: PatchHeatmap; width: number; height: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const region = heatmapCoveredRegion(width, height);

  useEffect(() => {
    const context = canvas.current?.getContext("2d");
    if (!context) return;
    const pixels = context.createImageData(HEATMAP_GRID, HEATMAP_GRID);
    heatmapIntensities(heatmap).forEach((value, index) => {
      if (value < HEATMAP_FLOOR) return;
      const t = (value - HEATMAP_FLOOR) / (1 - HEATMAP_FLOOR);
      pixels.data.set([182, 238, 82, Math.round((0.18 + 0.72 * t) * 255)], index * 4);
    });
    context.putImageData(pixels, 0, 0);
  }, [heatmap]);

  return (
    <canvas
      ref={canvas}
      width={HEATMAP_GRID}
      height={HEATMAP_GRID}
      role="img"
      aria-label="Patch map of the areas that influenced the detector most"
      className="absolute [image-rendering:pixelated]"
      style={{ left: `${region.x * 100}%`, top: `${region.y * 100}%`, width: `${region.width * 100}%`, height: `${region.height * 100}%` }}
    />
  );
}

/** Shown while a link or photo is being checked. */
export function AnalyzingView({ preview, onCancel }: { preview: string | null; onCancel: () => void }) {
  return (
    <div className="@container">
      <div role="status" className="grid overflow-hidden rounded-[3px] border border-rule bg-label @3xl:grid-cols-2">
        <div className="flex min-h-56 items-center justify-center border-b border-rule bg-well p-7 @3xl:min-h-[440px] @3xl:border-r @3xl:border-b-0">
          {preview ? (
            <div className="relative">
              <CropMarks detector={false} />
              {/* eslint-disable-next-line @next/next/no-img-element -- in-memory preview of the photo being checked */}
              <img src={preview} alt="" className="block max-h-[360px] max-w-full object-contain" />
            </div>
          ) : (
            <Spinner className="size-8 text-accent" />
          )}
        </div>
        <div className="flex flex-col gap-6 p-4 @3xl:p-6">
          <div className="flex items-center gap-3">
            <Spinner className="size-5 text-accent" />
            <div>
              <p className="font-semibold">Checking image…</p>
              <p className="text-small text-muted">Looking at lighting, edges and texture.</p>
            </div>
          </div>
          <div aria-hidden className="flex flex-col gap-3">
            {[56, 100, 92, 70].map((width) => (
              <span key={width} className="h-3 animate-pulse rounded-full bg-well" style={{ width: `${width}%` }} />
            ))}
          </div>
          <Button variant="secondary" onClick={onCancel} className="self-start">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

/** Shares the result as text, or copies it where the Web Share API isn't available. */
export function ShareResultButton({ item }: { item: VerificationCase }) {
  const [copied, setCopied] = useState(false);
  const share = async () => {
    const text = shareText(item);
    if (navigator.share) {
      await navigator.share({ text }).catch(() => {});
      return;
    }
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <Button icon={copied ? Check : Share} onClick={share}>
      {copied ? "Copied" : "Share result"}
    </Button>
  );
}
