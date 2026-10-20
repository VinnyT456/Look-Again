import type { BlueskyPost, FeedPage, FeedPost } from "../models/feed";

export const APPVIEW = "https://public.api.bsky.app/xrpc";
export const WHATS_HOT = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot";
export const FEED_PAGE_SIZE = 30;

/** Parses `https://bsky.app/profile/{handle-or-did}/post/{rkey}` into its parts. */
export function parsePostLink(link: string): { actor: string; rkey: string } | null {
  let trimmed = link.trim();
  if (!trimmed.toLowerCase().startsWith("http")) trimmed = `https://${trimmed}`;
  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return null;
  }
  const host = url.hostname.toLowerCase();
  if (host !== "bsky.app" && !host.endsWith(".bsky.app")) return null;
  const parts = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (parts.length < 4 || parts[0] !== "profile" || parts[2] !== "post") return null;
  return { actor: parts[1], rkey: parts[3] };
}

/** Finds the first Bluesky post link in shared text, or null when there isn't one. */
export function linkIn(text: string): string | null {
  return (
    text
      .split(/\s+/)
      .map((word) => word.replace(/^[<>()"',.]+|[<>()"',.]+$/g, ""))
      .find((word) => parsePostLink(word) !== null) ?? null
  );
}

export const threadUrl = (actor: string, rkey: string) =>
  `${APPVIEW}/app.bsky.feed.getPostThread?uri=${encodeURIComponent(`at://${actor}/app.bsky.feed.post/${rkey}`)}&depth=0&parentHeight=0`;

export function feedUrl(cursor: string | null, feed = WHATS_HOT) {
  let url = `${APPVIEW}/app.bsky.feed.getFeed?feed=${encodeURIComponent(feed)}&limit=${FEED_PAGE_SIZE}`;
  if (cursor) url += `&cursor=${encodeURIComponent(cursor)}`;
  return url;
}

interface ImageView {
  thumb?: string;
  fullsize?: string;
  alt?: string;
  aspectRatio?: { width: number; height: number };
}
interface Embed {
  images?: ImageView[];
  /** `app.bsky.embed.recordWithMedia#view`. */
  media?: { images?: ImageView[] };
}
interface Label {
  val: string;
}
interface PostView {
  uri: string;
  author: { handle: string; displayName?: string; avatar?: string; labels?: Label[] };
  record?: { text?: string };
  embed?: Embed;
  labels?: Label[];
  indexedAt?: string;
}

const imagesOf = (embed?: Embed) => embed?.images ?? embed?.media?.images ?? [];

/** Reads a getPostThread body; null when there's no post. Throws `"noImage"` when it has no photo. */
export function postFromThread(body: unknown, rkey: string): BlueskyPost | null {
  const post = (body as { thread?: { post?: PostView } })?.thread?.post;
  if (!post?.author?.handle) return null;
  const image = imagesOf(post.embed).find((view) => view.fullsize)?.fullsize;
  if (!image) throw new Error("noImage");
  return {
    authorHandle: post.author.handle,
    text: post.record?.text ?? "",
    postUrl: `https://bsky.app/profile/${post.author.handle}/post/${rkey}`,
    imageUrl: image,
  };
}

/**
 * Keeps posts with at least one image and no moderation or self labels on
 * the post or its author. Labels flag adult, graphic or otherwise sensitive
 * content, so anything labelled is left out entirely.
 */
export function feedPostFrom(post: PostView): FeedPost | null {
  if (post.labels?.length || post.author.labels?.length) return null;
  const images = imagesOf(post.embed);
  const first = images[0];
  if (!first?.thumb) return null;
  const rkey = post.uri.split("/").pop();
  if (!rkey) return null;
  const ratio = first.aspectRatio && first.aspectRatio.height > 0 ? first.aspectRatio.width / first.aspectRatio.height : null;
  const postedAt = post.indexedAt ? Date.parse(post.indexedAt) : NaN;
  return {
    id: post.uri,
    authorHandle: post.author.handle,
    authorName: post.author.displayName || post.author.handle,
    avatarUrl: post.author.avatar ?? null,
    text: post.record?.text ?? "",
    postUrl: `https://bsky.app/profile/${post.author.handle}/post/${rkey}`,
    thumbUrl: first.thumb,
    fullsizeUrl: first.fullsize ?? first.thumb,
    imageAlt: first.alt ?? "",
    aspectRatio: ratio,
    postedAt: Number.isNaN(postedAt) ? null : postedAt,
    imageCount: images.length,
  };
}

/** Turns a getFeed body into a page of safe image posts. */
export function feedPageFrom(body: unknown): FeedPage {
  const decoded = body as { feed?: { post: PostView }[]; cursor?: string };
  return {
    posts: (decoded.feed ?? []).map((item) => feedPostFrom(item.post)).filter((post): post is FeedPost => post !== null),
    cursor: decoded.cursor ?? null,
  };
}

/** Only Bluesky's own image CDN is fetched server-side, so the check route can't be used to reach other hosts. */
export function isBlueskyImageUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && (url.hostname === "cdn.bsky.app" || url.hostname.endsWith(".cdn.bsky.app"));
  } catch {
    return false;
  }
}
