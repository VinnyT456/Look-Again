# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js (App Router, TypeScript, Tailwind CSS) for the web app, a Manifest V3 browser extension sharing its components, and a FastAPI service under `ml/` that runs the detector. Chosen by the user during planning.

## Users

Two audiences, general public first:

- Northwestern students and community members who see a striking photo on Bluesky and want to know, before sharing, whether it is real, edited, or AI-generated. They arrive mid-scroll, curious or suspicious, usually on a laptop.
- Student journalists and fact-checkers who verify images as part of their work and need a quick, honest second opinion plus the habits to check sources themselves.

## Product Purpose

WildcatVerify checks Bluesky photos (by post link, by uploaded photo, or straight from a feed) with an AI-image detector, explains the result in plain language, and teaches people to look again for themselves through practice rounds and a clue guide. Success is a user who shares fewer fakes and knows why a photo is or isn't trustworthy.

## Positioning

A detector that says what it can't do. It answers only Likely Real or Likely AI, caps confidence at 99%, labels demo results, shows where the detector looked (heatmap) without calling it proof, and pairs every verdict with things to check yourself. The Look Again game trains judgment the detector can't replace, including real photos with false stories.

## Operating Context

- This record covers `apps/web` and its browser extension. The native apps in `apps/ios` and `apps/android` are the reference for behavior and copy, not for the web's look.
- Bluesky is the only source network. Posts are read through the public AppView (`public.api.bsky.app`), no sign-in.
- The Feed shows image posts from Bluesky's public What's Hot feed and hides anything carrying moderation or self labels.
- The browser extension mirrors the phone share sheet: check an image or post where you found it, see the result, Done discards it.

## Capabilities and Constraints

- Detector: CommunityForensics ViT with a rich linear probe, 384x384 center crop, threshold 0.5, outputs a fake probability and a 24x24 patch heatmap. It never answers Likely Edited; that verdict exists only in bundled examples and practice.
- On the web the detector runs on a private FastAPI service, not in the browser. If it is unreachable, results come from a labelled demo classifier.
- Sections: Check, Feed, My Checks, Learn and Settings. The native apps put Check in the center tab; the web leads with it.
- My Checks is in memory by default; Keep My Checks (opt-in) stores results on this device only. Erase All Data removes everything.
- Terminology: "Likely Real", "Likely Edited", "Likely AI", "Things to check yourself", "Look Again", "Clue Guide", "My Checks", "False story".

## Brand Commitments

- Name: WildcatVerify. Northwestern University context.
- Verdict meanings are fixed everywhere: green for real, amber for edited, red for AI, always with a word and a mark beside the color.
- The web and extension have their own visual world, chosen by the user; only the product truth is shared with the native apps, whose look (Northwestern purple, magnifier logo) the web does not copy.
- Voice: plain, calm, never more certain than the evidence. Copy is shared with the native apps.

## Evidence on Hand

- Practice bank of Look Again cases (text descriptions, `.example` handles so no real account is labelled fake).
- Three demo example results (Lakefill storm clouds, altered student council sign, Lake Michigan monorail), always marked demo.
- No testimonials, usage numbers, or accuracy benchmarks exist. None may be invented.

## Product Principles

1. Never overclaim: every verdict is "likely", demos are labelled, and the heatmap is described as influence, not proof.
2. A working tool, not a pitch: the first screen is the check itself.
3. Teach the habit, not just the answer: every result points to what the user can verify themselves.
4. Private by default: nothing is kept unless the user turns it on.
5. One product across platforms: the same sections, words and verdict meanings on phone, web and extension, even where the look differs.

## Accessibility & Inclusion

Matches the native apps: works with screen readers (verdicts are announced), respects reduced motion, supports dark mode and large text, and never encodes meaning in color alone (icons and words accompany every verdict color).
