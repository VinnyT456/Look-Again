import type { VerdictType } from "./verdict";

/** A normalized rectangle (0–1 in image space) marking the region that drove a verdict. */
export interface HotspotArea {
  xRatio: number;
  yRatio: number;
  widthRatio: number;
  heightRatio: number;
  label: string;
}

/**
 * The detector's per-patch map: how much each 16×16 patch of the 384×384
 * center crop pushed the decision toward "AI" (positive) or away (negative),
 * in logit units. It covers only part of the decision; the rest comes from
 * whole-image features that have no location.
 */
export interface PatchHeatmap {
  /** Row-major, `HEATMAP_GRID × HEATMAP_GRID`. */
  values: number[];
}

/** Output of the authenticity model. */
export interface ClassificationResult {
  verdict: VerdictType;
  /** 0–1, the winning side's probability. */
  confidence: number;
  hotspot: HotspotArea | null;
  heatmap: PatchHeatmap | null;
  /** True when the verdict did not come from the trained model. */
  isDemo: boolean;
}

export const HEATMAP_GRID = 24;
/** Mirrors the detector's preprocessing: short edge resized to 440, centre 384 kept. */
const SHORT_EDGE = 440;
const CROP_SIZE = 384;

/** Whether any patch pushed toward "AI" at all. */
export const heatmapHasSignal = (heatmap: PatchHeatmap) => Math.max(...heatmap.values) > 0;

/**
 * 0–1 per cell: positive contributions relative to the strongest one.
 * Cells that pushed toward "real" are 0, so only suspicious areas show.
 */
export function heatmapIntensities(heatmap: PatchHeatmap): number[] {
  const peak = Math.max(...heatmap.values);
  if (peak <= 0) return heatmap.values.map(() => 0);
  return heatmap.values.map((value) => Math.max(value, 0) / peak);
}

export interface HeatmapPeak {
  row: number;
  column: number;
  /** 0–1, relative to the strongest cell. */
  strength: number;
}

/**
 * The strongest cells, strongest first, each at least `spacing` cells from
 * the others so neighbours of one hot area don't count twice.
 */
export function heatmapPeaks(heatmap: PatchHeatmap, count = 3, minStrength = 0.45, spacing = 4): HeatmapPeak[] {
  const peaks: HeatmapPeak[] = [];
  const cells = heatmapIntensities(heatmap)
    .map((strength, index) => ({ row: Math.floor(index / HEATMAP_GRID), column: index % HEATMAP_GRID, strength }))
    .filter((cell) => cell.strength >= minStrength)
    .sort((a, b) => b.strength - a.strength);
  for (const cell of cells) {
    if (peaks.length === count) break;
    if (peaks.every((peak) => Math.max(Math.abs(peak.row - cell.row), Math.abs(peak.column - cell.column)) >= spacing)) peaks.push(cell);
  }
  return peaks;
}

/** "Upper left", "Center", "Lower right" and so on, for a cell of the grid. */
export function cellPlace(row: number, column: number) {
  const band = (n: number) => Math.min(2, Math.floor((n / HEATMAP_GRID) * 3));
  const vertical = ["Upper", "Middle", "Lower"][band(row)];
  const horizontal = ["left", "center", "right"][band(column)];
  if (vertical === "Middle") return horizontal === "center" ? "Center" : `Middle ${horizontal}`;
  return `${vertical} ${horizontal}`;
}

/** The part of the full image the model actually looked at, as fractions of width and height. */
export function heatmapCoveredRegion(width: number, height: number) {
  if (width <= 0 || height <= 0) return { x: 0, y: 0, width: 1, height: 1 };
  const side = (CROP_SIZE / SHORT_EDGE) * Math.min(width, height);
  const fx = Math.min(side / width, 1);
  const fy = Math.min(side / height, 1);
  return { x: (1 - fx) / 2, y: (1 - fy) / 2, width: fx, height: fy };
}
