import "server-only";

import type { ClassificationResult } from "../models/classification";
import { CheckError } from "../models/errors";
import { demoClassify } from "./demo-classifier";

/** The private FastAPI model service (`ml/src/look_again/serve`). */
export const detectorUrl = () => process.env.DETECTOR_URL ?? "http://127.0.0.1:8765";

interface ClassifyResponse {
  verdict: "real" | "ai";
  confidence: number;
  heatmap: { values: number[] } | null;
}

/** Whether the real model is loaded and answering. */
export async function detectorIsReady() {
  try {
    const response = await fetch(`${detectorUrl()}/health`, { signal: AbortSignal.timeout(2_000), cache: "no-store" });
    if (!response.ok) return false;
    return ((await response.json()) as { model_loaded?: boolean }).model_loaded === true;
  } catch {
    return false;
  }
}

/** Classifies with the detector service, falling back to the labelled demo classifier when it's unavailable. */
export async function classify(image: Blob): Promise<ClassificationResult> {
  const form = new FormData();
  form.append("file", image, "image");
  let response: Response;
  try {
    response = await fetch(`${detectorUrl()}/v1/classify`, {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    return demoClassify(await image.arrayBuffer());
  }
  if (response.status === 422) throw new CheckError("unreadablePhoto");
  if (response.status === 413) throw new CheckError("tooLarge");
  if (!response.ok) return demoClassify(await image.arrayBuffer());
  const body = (await response.json()) as ClassifyResponse;
  return {
    verdict: body.verdict,
    confidence: body.confidence,
    hotspot: null,
    heatmap: body.heatmap ? { values: body.heatmap.values } : null,
    isDemo: false,
  };
}
