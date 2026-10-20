"use client";

import { ArrowRight, ImageOff, RotateCcw, SearchX, WifiOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { FeedPost } from "@/lib/models/feed";
import type { VerificationCase } from "@/lib/models/verification-case";
import { app, closeFeedPost, loadFeed, loadMoreFeed, openFeedPost } from "@/lib/store/app";
import { useStore } from "@/lib/store/store";

import { AnalyzingView, ResultsView } from "./results";
import { BackBar, PageHeader } from "./shell";
import { Button, EmptyState, Spinner, VerdictTag } from "./ui";

/** Image posts from Bluesky's What's Hot feed. Pick one to check its first photo. */
export function FeedScreen() {
  const posts = useStore(app, (s) => s.feedPosts);
  const status = useStore(app, (s) => s.feedStatus);
  const error = useStore(app, (s) => s.feedError);
  const loadingMore = useStore(app, (s) => s.feedLoadingMore);
  const open = useStore(app, (s) => s.feedOpen);
  const cases = useStore(app, (s) => s.cases);

  useEffect(() => {
    void loadFeed();
  }, []);

  if (open) return <FeedCheck post={open} />;

  return (
    <div>
      <PageHeader
        title="Feed"
        description="Image posts from Bluesky's public What's Hot feed. Posts carrying content labels are hidden."
        actions={
          <Button variant="secondary" icon={RotateCcw} onClick={() => void loadFeed(true)} disabled={status === "loading"}>
            Refresh
          </Button>
        }
      />
      {status === "failed" ? (
        <EmptyState title="Couldn't load the feed" icon={WifiOff} description={error ?? undefined} action={{ label: "Try again", onClick: () => void loadFeed(true) }} />
      ) : status !== "loaded" && posts.length === 0 ? (
        <div role="status" className="flex items-center gap-3 py-24 text-muted">
          <Spinner />
          Loading posts…
        </div>
      ) : (
        <>
          {posts.length === 0 && <EmptyState title="No image posts right now" icon={ImageOff} description="Refresh to try again." />}
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {posts.map((post) => (
              <li key={post.id} className="flex">
                <FeedTile post={post} checked={cases.find((item) => item.postUrl === post.postUrl)} />
              </li>
            ))}
          </ul>
          <LoadMoreSentinel key={posts.length} />
          {loadingMore && (
            <div className="flex justify-center p-6">
              <Spinner label="Loading more posts" />
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** Loads the next page as the end of the list scrolls near. */
function LoadMoreSentinel() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => entry.isIntersecting && void loadMoreFeed(), { rootMargin: "800px" });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return <div ref={ref} aria-hidden />;
}

const relativeTime = new Intl.RelativeTimeFormat(undefined, { numeric: "auto", style: "short" });

function postedAgo(postedAt: number | null, now: number) {
  if (postedAt === null) return null;
  const minutes = Math.round((postedAt - now) / 60_000);
  if (Math.abs(minutes) < 60) return relativeTime.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return relativeTime.format(hours, "hour");
  return relativeTime.format(Math.round(hours / 24), "day");
}

/** One post: the image, who posted it and when, its text, and either its verdict or a check cue. */
function FeedTile({ post, checked }: { post: FeedPost; checked: VerificationCase | undefined }) {
  const [now] = useState(() => Date.now());
  const ago = postedAgo(post.postedAt, now);
  return (
    <button
      type="button"
      onClick={() => void openFeedPost(post)}
      aria-label={`Check the first image in this post by ${post.authorName}`}
      className="group flex w-full flex-col overflow-hidden rounded-[3px] border border-rule bg-label text-left transition-[border-color,box-shadow] duration-150 hover:border-rule-strong hover:shadow-[0_6px_20px_-10px_rgb(0_0_0/0.3)]"
    >
      {/* Previews are cropped to one shape so the grid aligns; the check itself always uses the full image. */}
      <span className="relative block aspect-[4/3] overflow-hidden bg-well">
        {/* eslint-disable-next-line @next/next/no-img-element -- Bluesky CDN thumbnail */}
        <img src={post.thumbUrl} alt={post.imageAlt || "Post image"} loading="lazy" className="absolute inset-0 size-full object-cover transition-transform duration-300 ease-out-expo group-hover:scale-[1.02]" />
        {post.imageCount > 1 && <span className="absolute top-2 right-2 rounded-md bg-label px-2 py-1 text-small font-semibold">1 of {post.imageCount}</span>}
      </span>
      <span className="flex flex-1 flex-col gap-2 p-4">
        <span className="flex items-center gap-2.5">
          {post.avatarUrl ? (
            // eslint-disable-next-line @next/next/no-img-element -- Bluesky CDN avatar
            <img src={post.avatarUrl} alt="" loading="lazy" className="size-8 shrink-0 rounded-full bg-well object-cover" />
          ) : (
            <span className="size-8 shrink-0 rounded-full bg-well" />
          )}
          <span className="min-w-0">
            <span className="block truncate font-semibold">{post.authorName}</span>
            <span className="block truncate text-small text-muted" suppressHydrationWarning>
              {[`@${post.authorHandle}`, ago].filter(Boolean).join(" · ")}
            </span>
          </span>
        </span>
        {post.text && <span className="line-clamp-2 text-pretty">{post.text}</span>}
        <span className="mt-auto flex items-center gap-2 border-t border-rule pt-3">
          {checked ? (
            <>
              <VerdictTag verdict={checked.verdict} />
              <span className="text-small text-muted">{checked.confidencePercentage}% · checked</span>
            </>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-small font-semibold text-muted transition-colors group-hover:text-accent group-focus-visible:text-accent">
              Check this post
              <ArrowRight aria-hidden className="size-4 transition-transform duration-150 group-hover:translate-x-0.5" />
            </span>
          )}
        </span>
      </span>
    </button>
  );
}

/** One feed post being checked, then its result. The result is added to My Checks. */
function FeedCheck({ post }: { post: FeedPost }) {
  const check = useStore(app, (s) => s.feedCheck);
  const showHeatmap = useStore(app, (s) => s.settings.showHeatmap);

  return (
    <div>
      <BackBar label="Feed" onBack={closeFeedPost} />
      {check?.kind === "result" ? (
        <ResultsView item={check.item} imageSrc={check.item.imageUrl} showHeatmap={showHeatmap} />
      ) : check?.kind === "failed" ? (
        <EmptyState title="Couldn't check this post" icon={SearchX} description={check.message} action={{ label: "Try again", onClick: () => void openFeedPost(post) }} />
      ) : (
        <AnalyzingView preview={post.thumbUrl} onCancel={closeFeedPost} />
      )}
    </div>
  );
}
