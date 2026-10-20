import {
  Aperture,
  Calendar,
  Camera,
  Check,
  Copy,
  Flag,
  Frame,
  Glasses,
  Grid3x3,
  Hand,
  MessagesSquare,
  PenLine,
  ScanSearch,
  Sparkles,
  Sun,
  SunDim,
  Tag,
  TextQuote,
  TriangleAlert,
  Undo2,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { ClueIcon } from "@/lib/learn/clues";
import type { VerdictType } from "@/lib/models/verdict";

export const verdictIcon: Record<VerdictType, LucideIcon> = {
  real: Check,
  tampered: TriangleAlert,
  ai: Sparkles,
};

export const clueIcon: Record<ClueIcon, LucideIcon> = {
  sun: Sun,
  hand: Hand,
  users: Users,
  grid: Grid3x3,
  glasses: Glasses,
  handRaised: Hand,
  sunDim: SunDim,
  aperture: Aperture,
  copy: Copy,
  flag: Flag,
  frame: Frame,
  scribble: PenLine,
  tag: Tag,
  undo: Undo2,
  messages: MessagesSquare,
  calendar: Calendar,
  camera: Camera,
  altText: TextQuote,
  ai: Sparkles,
  edited: TriangleAlert,
  source: ScanSearch,
};

/** Tailwind classes per verdict, so none are built from strings at runtime. */
export const verdictTone: Record<VerdictType, { solid: string; ink: string; wash: string }> = {
  real: { solid: "bg-real", ink: "text-real", wash: "bg-real-wash" },
  tampered: { solid: "bg-edited", ink: "text-edited", wash: "bg-edited-wash" },
  ai: { solid: "bg-ai", ink: "text-ai", wash: "bg-ai-wash" },
};
