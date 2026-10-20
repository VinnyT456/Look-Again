/** Failures with copy the user can act on. */
export type CheckErrorCode =
  | "invalidLink"
  | "postNotFound"
  | "noImage"
  | "network"
  | "unreadablePhoto"
  | "unsupported"
  | "tooLarge";

export const checkErrorMessages: Record<CheckErrorCode, string> = {
  invalidLink: "That doesn't look like a Bluesky post link. It should look like bsky.app/profile/…/post/…",
  postNotFound: "We couldn't find that post. It may be deleted or private.",
  noImage: "That post doesn't have a photo to check.",
  network: "Couldn't reach Bluesky. Check your connection and try again.",
  unreadablePhoto: "We couldn't open that photo. Try a different image or screenshot.",
  unsupported:
    "WildcatVerify can check photos, screenshots and Bluesky post links. Try the image itself or the post's link.",
  tooLarge: "That photo is too large to check. Try one under 20 MB.",
};

export const genericCheckError = "Something went wrong checking that image. Please try again.";

export class CheckError extends Error {
  constructor(readonly code: CheckErrorCode) {
    super(checkErrorMessages[code]);
  }
}

/** User-facing copy for any failure. */
export const userMessage = (error: unknown, fallback = genericCheckError) =>
  error instanceof CheckError ? error.message : fallback;
