import type { ClassificationResult, HotspotArea } from "../models/classification";
import { verdicts } from "../models/verdict";

const hotspots: Record<string, HotspotArea | null> = {
  real: null,
  tampered: { xRatio: 0.28, yRatio: 0.3, widthRatio: 0.44, heightRatio: 0.32, label: "Possible edit" },
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
  const verdict = verdicts[digest[0] % verdicts.length];
  return {
    verdict,
    confidence: 0.8 + (digest[1] % 19) / 100,
    hotspot: hotspots[verdict],
    heatmap: null,
    isDemo: true,
  };
}
