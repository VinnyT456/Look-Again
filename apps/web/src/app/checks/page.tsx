import type { Metadata } from "next";

import { HistoryScreen } from "@/components/history-screen";

export const metadata: Metadata = { title: "My Checks" };

export default function ChecksPage() {
  return <HistoryScreen />;
}
