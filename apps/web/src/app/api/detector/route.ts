import { detectorIsReady } from "@/lib/check/detector";

/** Whether checks are coming from the real model or the demo classifier, for Settings. */
export async function GET() {
  return Response.json({ ready: await detectorIsReady() });
}
