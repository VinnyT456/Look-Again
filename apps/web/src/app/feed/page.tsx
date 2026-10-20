import type { Metadata } from "next";

import { FeedScreen } from "@/components/feed-screen";

export const metadata: Metadata = { title: "Feed" };

export default function FeedPage() {
  return <FeedScreen />;
}
