import type { ClassificationResult, HotspotArea, PatchHeatmap } from "./classification";
import { verdictCopy, verdictLabel, type VerdictType } from "./verdict";

/** One checked image: where it came from, what the classifier said, and why. */
export interface VerificationCase {
  id: string;
  title: string;
  authorHandle: string;
  postUrl: string | null;
  caption: string;
  /** Epoch milliseconds; null for the bundled examples, which use `timeAgo`. */
  checkedAt: number | null;
  timeAgo?: string;
  /** Null when there is no photo to show (e.g. the bundled examples). */
  imageUrl: string | null;
  verdict: VerdictType;
  confidencePercentage: number;
  plainSummary: string;
  suggestedAction: string;
  detectedIssue: string | null;
  hotspot: HotspotArea | null;
  /** Where the detector found what pushed it toward "AI" (detector results only). */
  heatmap: PatchHeatmap | null;
  keyFindings: string[];
  /**
   * True when the verdict did not come from the trained model (bundled
   * examples, or the demo classifier). Always shown to the user.
   */
  isDemo: boolean;
}

/** Uploaded photos live only in memory and are addressed with this scheme. */
export const inMemoryImageUrl = (id: string) => `memory://upload/${id}`;
export const isInMemoryImage = (url: string) => url.startsWith("memory://");

/** First line of the post, trimmed to fit a list row. */
export function caseTitle(text: string) {
  const firstLine = text.split("\n").find((line) => line.length > 0) ?? "";
  if (!firstLine) return "Bluesky post";
  return firstLine.length > 60 ? `${firstLine.slice(0, 59)}…` : firstLine;
}

export function makeCase(
  result: ClassificationResult,
  source: { id?: string; title: string; authorHandle: string; postUrl: string | null; caption: string; imageUrl: string | null },
): VerificationCase {
  const copy = verdictCopy[result.verdict];
  return {
    id: source.id ?? crypto.randomUUID(),
    title: source.title,
    authorHandle: source.authorHandle,
    postUrl: source.postUrl,
    caption: source.caption,
    checkedAt: Date.now(),
    imageUrl: source.imageUrl,
    verdict: result.verdict,
    // Never display certainty: 99.9% would otherwise round to "100%".
    confidencePercentage: Math.min(99, Math.round(result.confidence * 100)),
    plainSummary: copy.summary,
    suggestedAction: copy.action,
    detectedIssue: result.hotspot?.label ?? null,
    hotspot: result.hotspot,
    heatmap: result.heatmap,
    keyFindings: copy.findings,
    isDemo: result.isDemo,
  };
}

/** Title of photos checked from the browser extension's image menu, which have no post around them. */
export const BROWSING_TITLE = "Photo in Bluesky";

/** Uploaded photos have no author. */
export function displayHandle(item: VerificationCase) {
  if (item.authorHandle) return `@${item.authorHandle}`;
  return item.title === BROWSING_TITLE ? "Checked while browsing Bluesky" : "From your photos";
}

/** "Just now", "5m ago", "3h ago", or a date. */
export function timeAgo(item: VerificationCase, now = Date.now()) {
  if (item.checkedAt == null) return item.timeAgo ?? "";
  const minutes = Math.floor((now - item.checkedAt) / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(item.checkedAt).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Plain-text summary used by sharing. */
export function shareText(item: VerificationCase) {
  return [
    `WildcatVerify${item.isDemo ? " (demo result)" : ""}: ${verdictLabel[item.verdict]}, ${item.confidencePercentage}% confidence`,
    item.title,
    item.authorHandle ? `Posted by @${item.authorHandle}` : null,
    item.plainSummary,
    item.postUrl,
  ]
    .filter(Boolean)
    .join("\n");
}
