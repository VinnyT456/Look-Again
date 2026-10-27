import type { ClassificationResult, HotspotArea } from "../models/classification";
import type { VerdictType } from "../models/verdict";

// Like the detector, the demo answers only Likely Real or Likely AI; Likely Edited is for examples and practice.
const outcomes: VerdictType[] = ["real", "ai"];

const hotspots: Record<string, HotspotArea | null> = {
  real: null,
  ai: { xRatio: 0.2, yRatio: 0.22, widthRatio: 0.6, heightRatio: 0.5, label: "Synthetic texture" },
};

/**
 * Fallback when the detector service can't be reached. Deterministic per image
 * (hash of its bytes) so re-checking the same photo gives the same answer.
 * Every result it produces is labelled as a demo.
 */
export async function demoClassify(bytes: ArrayBuffer): Promise<ClassificationResult> {
  await new Promise((resolve) => setTimeout(resolve, 1200));
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  const verdict = outcomes[digest[0] % outcomes.length];
  return {
    verdict,
    confidence: 0.8 + (digest[1] % 19) / 100,
    hotspot: hotspots[verdict],
    heatmap: null,
    isDemo: true,
  };
}
