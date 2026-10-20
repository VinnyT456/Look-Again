import type { VerdictType } from "../models/verdict";

/** Icon names resolved to lucide icons in `components/icons.tsx`. */
export type ClueIcon =
  | "sun"
  | "hand"
  | "users"
  | "grid"
  | "glasses"
  | "handRaised"
  | "sunDim"
  | "aperture"
  | "copy"
  | "flag"
  | "frame"
  | "scribble"
  | "tag"
  | "undo"
  | "messages"
  | "calendar"
  | "camera"
  | "altText"
  | "ai"
  | "edited"
  | "source";

export interface Clue {
  title: string;
  detail: string;
  icon: ClueIcon;
}

/** The "What to look for" guide, grouped by the kind of problem. */
export interface ClueGroup {
  id: string;
  title: string;
  shortTitle: string;
  /** One line on the Learn home describing the group. */
  summary: string;
  icon: ClueIcon;
  /** The verdict these clues help you reach; picks which group to review after a round. */
  focus: VerdictType;
  clues: Clue[];
}

export const clueGuide: ClueGroup[] = [
  {
    id: "ai",
    title: "Signs of AI",
    shortTitle: "AI",
    summary: "What generated images still get wrong",
    icon: "ai",
    focus: "ai",
    clues: [
      { title: "Lighting", detail: "Highlights, shadows and reflections should all come from the same lights. Generators often light each part of a picture on its own.", icon: "sun" },
      { title: "Things touching", detail: "Look where objects meet: fingers and cups, water and legs, hair and collars. Generated objects tend to blend into each other.", icon: "hand" },
      { title: "The background", detail: "Faces, signs and buildings at the back get less attention from a generator. Look for faces without features and lettering that spells nothing.", icon: "users" },
      { title: "Patterns", detail: "Windows, tiles, fences and keyboard keys should repeat evenly. Watch for rows that drift or merge.", icon: "grid" },
      { title: "Pairs", detail: "Earrings, glasses arms and shoes often don't match left to right.", icon: "glasses" },
      { title: "Hands and teeth", detail: "Extra fingers and blurred teeth were common in older generators. Newer ones rarely make these mistakes, so good hands don't prove a photo is real.", icon: "handRaised" },
    ],
  },
  {
    id: "editing",
    title: "Signs of editing",
    shortTitle: "Editing",
    summary: "Where part of a real photo was changed",
    icon: "edited",
    focus: "tampered",
    clues: [
      { title: "Shadows", detail: "Everyone outdoors shares one sun. A shadow pointing the wrong way, or a person lit differently from the crowd, was probably added.", icon: "sunDim" },
      { title: "Sharpness and grain", detail: "Things the same distance from the camera should be equally sharp and equally grainy. A crisp object in a soft scene stands out.", icon: "aperture" },
      { title: "Copies", detail: "The same person, cloud or brick showing up twice means part of the picture was copied to fill space.", icon: "copy" },
      { title: "Text on things", detail: "Printed words bend with the surface they're on. Text that stays flat across folds or curves was pasted on.", icon: "flag" },
      { title: "Bent backgrounds", detail: "Door frames, tiles and walls that warp only next to a body mean the body was reshaped.", icon: "frame" },
      { title: "Edges", detail: "A thin outline or halo around a person or skyline is often where something was cut in.", icon: "scribble" },
    ],
  },
  {
    id: "source",
    title: "Check the source",
    shortTitle: "Source",
    summary: "Who posted it, and whether the story fits",
    icon: "source",
    focus: "real",
    clues: [
      { title: "Labels", detail: "Bluesky shows labels from the moderation services you use, and some of them label AI-generated images. In Bluesky, tap a label to see who added it.", icon: "tag" },
      { title: "The first post", detail: "Follow reposts and quote posts back to whoever posted it first, then look at what else that account shares.", icon: "undo" },
      { title: "Replies and quotes", detail: "People who were there, or who found the original, often say so in the replies.", icon: "messages" },
      { title: "Date and place", detail: "A real photo from another year or another city is still misleading. Watermarks and credits often give it away.", icon: "calendar" },
      { title: "Other angles", detail: "Big events get photographed by many people. If only one picture exists, wait before sharing it.", icon: "camera" },
      { title: "Alt text and credentials", detail: "Some posters describe how a picture was made in its alt text, and some files carry Content Credentials that record how they were made.", icon: "altText" },
    ],
  },
];

export const groupFor = (verdict: VerdictType) => clueGuide.find((group) => group.focus === verdict) ?? null;
