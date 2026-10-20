import type { Metadata } from "next";

import { LearnScreen } from "@/components/learn-screen";

export const metadata: Metadata = { title: "Learn" };

export default function LearnPage() {
  return <LearnScreen />;
}
