import { MAX_IMAGE_BYTES } from "@/lib/bluesky/service";
import { checkImageUrl, checkLink, checkPost, checkUpload } from "@/lib/check/pipeline";
import { CheckError } from "@/lib/models/errors";
import type { BlueskyPost } from "@/lib/models/feed";

import { errorResponse } from "../respond";

/**
 * Checks one image and returns a `VerificationCase`. Accepts:
 * - multipart `file`: an uploaded photo
 * - JSON `{ link }`: a Bluesky post link, resolved here
 * - JSON `{ post }`: a post the client already resolved (Feed, Check tab)
 * - JSON `{ imageUrl }`: a photo on Bluesky's CDN (browser extension)
 */
export async function POST(request: Request) {
  try {
    const type = request.headers.get("content-type") ?? "";
    if (type.startsWith("multipart/form-data")) {
      const file = (await request.formData()).get("file");
      if (!(file instanceof Blob) || file.size === 0) throw new CheckError("unreadablePhoto");
      if (file.size > MAX_IMAGE_BYTES) throw new CheckError("tooLarge");
      return Response.json(await checkUpload(file));
    }
    const body = (await request.json().catch(() => null)) as {
      link?: unknown;
      post?: Partial<BlueskyPost>;
      imageUrl?: unknown;
    } | null;
    if (typeof body?.link === "string") return Response.json(await checkLink(body.link));
    const post = body?.post;
    if (post && typeof post.imageUrl === "string") {
      return Response.json(
        await checkPost({
          imageUrl: post.imageUrl,
          authorHandle: String(post.authorHandle ?? ""),
          text: String(post.text ?? ""),
          postUrl: String(post.postUrl ?? ""),
        }),
      );
    }
    if (typeof body?.imageUrl === "string") return Response.json(await checkImageUrl(body.imageUrl));
    throw new CheckError("unsupported");
  } catch (error) {
    return errorResponse(error);
  }
}
