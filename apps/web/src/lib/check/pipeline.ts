import "server-only";

import { fetchBlueskyImage, fetchPost } from "../bluesky/service";
import type { BlueskyPost } from "../models/feed";
import { BROWSING_TITLE, caseTitle, makeCase, type VerificationCase } from "../models/verification-case";
import { classify } from "./detector";

/**
 * Turns a Bluesky post or raw image into a `VerificationCase`. Shared by the
 * Check tab, the Feed and the browser extension so all give identical results.
 */
export async function checkPost(post: BlueskyPost): Promise<VerificationCase> {
  const image = await fetchBlueskyImage(post.imageUrl);
  return makeCase(await classify(image), {
    title: caseTitle(post.text),
    authorHandle: post.authorHandle,
    postUrl: post.postUrl,
    caption: post.text,
    imageUrl: post.imageUrl,
  });
}

export async function checkLink(link: string) {
  return checkPost(await fetchPost(link));
}

/** A photo from Bluesky's CDN with no post around it (the extension's image menu). */
export async function checkImageUrl(imageUrl: string) {
  const image = await fetchBlueskyImage(imageUrl);
  return makeCase(await classify(image), {
    title: BROWSING_TITLE,
    authorHandle: "",
    postUrl: null,
    caption: "",
    imageUrl,
  });
}

/** An uploaded photo. It's classified and dropped; the client keeps its own copy to show. */
export async function checkUpload(image: Blob) {
  return makeCase(await classify(image), {
    title: "Uploaded photo",
    authorHandle: "",
    postUrl: null,
    caption: "",
    imageUrl: null,
  });
}
