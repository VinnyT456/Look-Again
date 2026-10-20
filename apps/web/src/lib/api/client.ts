import { genericCheckError } from "../models/errors";
import type { BlueskyPost, FeedPage, FeedPost } from "../models/feed";
import type { VerificationCase } from "../models/verification-case";

/** A failed API call, carrying the server's user-facing message. */
export class ApiError extends Error {}

/**
 * Talks to the Next.js API. The web app uses its own origin (`base = ""`);
 * the browser extension passes the server it was configured with.
 */
export function apiClient(base = "") {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${base}${path}`, { ...init, credentials: "omit" });
    } catch {
      throw new ApiError(
        base ? "Couldn't reach the WildcatVerify server. Check the server address in the extension's options." : "Couldn't reach WildcatVerify. Check your connection and try again.",
      );
    }
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError((body as { error?: string } | null)?.error ?? genericCheckError);
    return body as T;
  }

  const postJson = <T>(path: string, body: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });

  return {
    resolvePost: (link: string, signal?: AbortSignal) =>
      request<BlueskyPost>(`/api/bluesky/post?link=${encodeURIComponent(link)}`, { signal }),
    feedPage: (cursor: string | null) =>
      request<FeedPage>(`/api/bluesky/feed${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`),
    checkLink: (link: string, signal?: AbortSignal) => postJson<VerificationCase>("/api/check", { link }, signal),
    checkPost: (post: BlueskyPost, signal?: AbortSignal) => postJson<VerificationCase>("/api/check", { post }, signal),
    checkFeedPost: (post: FeedPost, signal?: AbortSignal) =>
      postJson<VerificationCase>(
        "/api/check",
        { post: { imageUrl: post.fullsizeUrl, authorHandle: post.authorHandle, text: post.text, postUrl: post.postUrl } },
        signal,
      ),
    checkImageUrl: (imageUrl: string, signal?: AbortSignal) => postJson<VerificationCase>("/api/check", { imageUrl }, signal),
    checkFile: (file: Blob, signal?: AbortSignal) => {
      const form = new FormData();
      form.append("file", file);
      return request<VerificationCase>("/api/check", { method: "POST", body: form, signal });
    },
    detectorReady: () => request<{ ready: boolean }>("/api/detector").then((body) => body.ready),
  };
}

export type ApiClient = ReturnType<typeof apiClient>;
