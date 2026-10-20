import "server-only";

import { CheckError } from "../models/errors";
import type { BlueskyPost, FeedPage } from "../models/feed";
import { feedPageFrom, feedUrl, isBlueskyImageUrl, parsePostLink, postFromThread, threadUrl } from "./parse";

const TIMEOUT_MS = 15_000;
export const MAX_IMAGE_BYTES = 20 * 1024 * 1024;

async function getJson(url: string): Promise<{ status: number; body: unknown }> {
  let response: Response;
  try {
    response = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS), headers: { Accept: "application/json" } });
  } catch {
    throw new CheckError("network");
  }
  if (!response.ok) return { status: response.status, body: null };
  try {
    return { status: response.status, body: await response.json() };
  } catch {
    return { status: 0, body: null };
  }
}

/** Reads a public post through the unauthenticated Bluesky AppView. */
export async function fetchPost(link: string): Promise<BlueskyPost> {
  const parsed = parsePostLink(link);
  if (!parsed) throw new CheckError("invalidLink");
  const { status, body } = await getJson(threadUrl(parsed.actor, parsed.rkey));
  if (status !== 200) throw new CheckError("postNotFound");
  try {
    const post = postFromThread(body, parsed.rkey);
    if (!post) throw new CheckError("postNotFound");
    return post;
  } catch (error) {
    if (error instanceof CheckError) throw error;
    throw new CheckError("noImage");
  }
}

/** One page of image posts from Bluesky's public What's Hot feed. */
export async function fetchFeedPage(cursor: string | null): Promise<FeedPage> {
  const { status, body } = await getJson(feedUrl(cursor));
  if (status !== 200) throw new CheckError("network");
  return feedPageFrom(body);
}

/** Downloads a photo from Bluesky's CDN, refusing any other host. */
export async function fetchBlueskyImage(url: string): Promise<Blob> {
  if (!isBlueskyImageUrl(url)) throw new CheckError("unsupported");
  let response: Response;
  try {
    response = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch {
    throw new CheckError("network");
  }
  if (!response.ok) throw new CheckError("network");
  const blob = await response.blob();
  if (blob.size > MAX_IMAGE_BYTES) throw new CheckError("tooLarge");
  return blob;
}
