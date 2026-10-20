/** A Bluesky post reduced to what the checker needs. */
export interface BlueskyPost {
  authorHandle: string;
  text: string;
  postUrl: string;
  imageUrl: string;
}

/** An image post from Bluesky's public "What's Hot" feed. */
export interface FeedPost {
  /** The post's AT URI. */
  id: string;
  authorHandle: string;
  authorName: string;
  avatarUrl: string | null;
  text: string;
  postUrl: string;
  thumbUrl: string;
  /** The full-resolution image, which is what gets checked. */
  fullsizeUrl: string;
  imageAlt: string;
  /** Width ÷ height of the first image, when Bluesky provides it. */
  aspectRatio: number | null;
  /** Epoch milliseconds. */
  postedAt: number | null;
  /** How many images the post has; only the first is checked. */
  imageCount: number;
}

/** One page of feed posts and the cursor for the next page (null at the end). */
export interface FeedPage {
  posts: FeedPost[];
  cursor: string | null;
}
