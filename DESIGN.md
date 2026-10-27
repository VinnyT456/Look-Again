---
name: WildcatVerify
description: Checks Bluesky photos like objects on a conservator's bench, with an honest condition report beside each one.
colors:
  wall: "#dddfe2"
  label: "#fbfbfc"
  well: "#eceef0"
  ink: "#1b1a1f"
  muted: "#4a4b52"
  rule: "#c8cacf"
  rule-strong: "#9fa1a8"
  uv: "#2e1d4d"
  uv-active: "#3d2963"
  on-uv: "#ede8f7"
  on-uv-muted: "#cfc6e3"
  accent: "#4b2f86"
  glow: "#b6ee52"
  ai: "#b42e25"
  real: "#2e6f4e"
  edited: "#8a5300"
  ai-wash: "#f6e4e2"
  real-wash: "#e2efe7"
  edited-wash: "#f5ead9"
  wall-dark: "#131217"
  label-dark: "#1e1d23"
  well-dark: "#26252c"
  ink-dark: "#ecebf0"
  muted-dark: "#aeadb6"
  rule-dark: "#34333b"
  rule-strong-dark: "#5a5963"
  uv-dark: "#1e1433"
  uv-active-dark: "#2f2150"
  accent-dark: "#c9b6f2"
  ai-dark: "#f08a80"
  real-dark: "#7fcf9f"
  edited-dark: "#e9b268"
  ai-wash-dark: "#3a1d1b"
  real-wash-dark: "#16301f"
  edited-wash-dark: "#352612"
typography:
  title:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 800
    lineHeight: "32px"
    letterSpacing: "-0.015em"
  heading:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: "24px"
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "24px"
  body-strong:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: "24px"
  label:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: "19px"
  label-strong:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: "19px"
  numeric:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 500
    lineHeight: "24px"
    fontFeature: "\"tnum\" 1"
rounded:
  sheet: "3px"
  control: "6px"
  track: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.uv}"
    textColor: "{colors.on-uv}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.uv-active}"
    textColor: "{colors.on-uv}"
  button-secondary:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
  button-quiet:
    textColor: "{colors.accent}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-danger:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ai}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-danger-hover:
    backgroundColor: "{colors.ai-wash}"
    textColor: "{colors.ai}"
  input-link:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    height: "56px"
  segmented-track:
    backgroundColor: "{colors.label}"
    rounded: "{rounded.track}"
    padding: "4px"
  segmented-option-active:
    backgroundColor: "{colors.uv}"
    textColor: "{colors.on-uv}"
    typography: "{typography.label-strong}"
    rounded: "{rounded.control}"
    height: "36px"
    padding: "0 14px"
  sheet:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
  bench:
    backgroundColor: "{colors.well}"
    padding: "24px"
  rail:
    backgroundColor: "{colors.uv}"
    textColor: "{colors.on-uv}"
    width: "240px"
    padding: "24px 16px"
  rail-link-active:
    backgroundColor: "{colors.uv-active}"
    textColor: "#ffffff"
    typography: "{typography.body-strong}"
    rounded: "{rounded.control}"
    height: "44px"
    padding: "0 12px"
  tab-bar-active:
    textColor: "{colors.accent}"
    height: "56px"
  verdict-mark-lg:
    backgroundColor: "{colors.ai}"
    textColor: "{colors.label}"
    rounded: "{rounded.full}"
    size: "48px"
  verdict-mark-md:
    rounded: "{rounded.full}"
    size: "36px"
  verdict-mark-sm:
    rounded: "{rounded.full}"
    size: "24px"
---

# Design System: WildcatVerify

## Overview

**Creative North Star: "The Condition Report"**

Every photo is handled like an object on a conservator's bench. It sits whole inside registration crop marks, is examined once in plain light and once under the detector's light, and gets a condition report beside it: the verdict set like a museum object label, then numbered notes the reader can check for themselves. The world draws on museum condition reports and UV examination. It's a working instrument, not a pitch, and it doesn't play the dark sci-fi scanner or put a confidence ring on a card.

The ground is a cool gallery wall. Results sit on one sheet of near-white label stock. The only saturated surface is a deep UV-violet rail. Fluorescent green appears only when the detector's light is on. Density is calm: one sheet per result, ruled rows inside it, and no floating cards stacked on cards. Rank comes from weight and ink, not from more sizes. The wall stays quiet so that the verdict inks and the fluorescence are the only loud things on screen.

Dark mode keeps the same roles in a darker room. The wall drops to near-black, the label stock to charcoal, the rail deepens, and the verdict inks lighten so they still clear 4.5:1.

**Key Characteristics:**
- Cool gallery wall, one label-stock sheet per result, 1px rules between rows.
- A UV-violet rail (desktop) or top bar (mobile) is the only saturated surface.
- Fluorescent glow appears only under detector light, plus two brand exceptions.
- One grotesk at three sizes; rank carried by weight and ink.
- The verdict is always mark + word + ink, never color alone.
- Photos are framed whole by registration crop marks and never tinted in plain light.

## Colors

The palette is a cool neutral museum room with one violet instrument, one fluorescent signal, and three fixed verdict inks.

### Primary
- **Deep UV Violet** (uv): the shell rail and mobile top bar, primary buttons, the active Segmented option, the toggle's on track, and the multiply wash that darkens a photo under detector light. In dark mode it deepens (uv-dark) and primary buttons switch to the pale accent.
- **UV Violet, Active** (uv-active): the hovered primary button and the active rail link. Active navigation text on it is pure white, not on-uv.
- **Examination Violet** (accent / accent-dark): links, quiet buttons, the focus outline (2px, offset 2px), the caret, selection tint (24% mix), note number rings, the active tab bar item, and link-row icons. In dark mode it becomes a pale lavender and takes over as the primary button fill, with wall-colored text.

### Secondary
- **Fluorescence** (glow): the detector's light. It is used for the 24×24 patch cells, the 1px leader line and its 3px end dot, the 4px ring around a focused mark, the flagged-area outline on demo results, crop marks under detector light, and mark pins in dark mode. Outside detector light it appears only as the detector-ready dot in the rail foot and the single lit cell of the wordmark glyph.

### Tertiary
- **Verdict Red** (ai / ai-dark): Likely AI. It also marks destructive actions (danger button text, delete hover) and the error banner, always on its wash.
- **Verdict Green** (real / real-dark): Likely Real.
- **Verdict Amber** (edited / edited-dark): Likely Edited. This verdict appears only in demos and practice.
- **Verdict Washes** (ai-wash, real-wash, edited-wash): quiet fills behind verdict-colored text, used for the error banner and danger hover.

### Neutral
- **Gallery Wall** (wall / wall-dark): the page ground behind everything.
- **Label Stock** (label / label-dark): the sheet a result, panel, register or dialog is printed on. It is also the text color on filled verdict marks.
- **Bench Well** (well / well-dark): the photo half of the bench, the idle drop frame, row hover, thumbnails, disabled fills, and skeleton bars.
- **Ink** (ink / ink-dark): primary text.
- **Secondary Ink** (muted / muted-dark): metadata, descriptions, table headers, and inactive tab labels.
- **Hairline** (rule / rule-dark): 1px sheet borders and row dividers.
- **Strong Rule** (rule-strong / rule-strong-dark): secondary button and input borders, crop marks in plain light, the detector scale track (at 45%), the caption quote bar, and scrollbars.
- **On-UV** (on-uv, on-uv-muted): text and icons on the rail. Muted is for inactive rail icons and rail-foot detail.

### Named Rules
**The Detector Light Rule.** Fluorescence (glow) means "the detector's light is on". It appears only under detector light (cells, leader lines, the focused-mark ring, crop marks, the demo flag outline), plus the detector-ready dot and the one lit cell of the wordmark. Never use it for buttons, links, success states or decoration.

**The Mark-and-Word Rule.** Each verdict ink always travels with its filled mark and its word. Results, rows and tiles use the full label ("Likely AI", "Likely Real", "Likely Edited"). The only short forms ("AI", "Real", "Edited") are the verdict filter chips.

**The White-on-Active Rule.** The current navigation item on the violet rail is pure white text and icon on uv-active, in semibold. Inactive items are on-uv text with on-uv-muted icons.

## Typography

**Display Font:** none. One family does all the work.
**Body Font:** Schibsted Grotesk (with ui-sans-serif, system-ui, sans-serif), loaded through next/font as `--font-grotesk`.

**Character:** A sourced newsroom grotesk, firm and legible at small sizes. It reads like the typed text on a museum label: plain, exact, and unhurried.

### Hierarchy
- **Title** (800, 28px / 32px, -0.015em): page titles and the verdict line on the object label. Balanced wrapping.
- **Heading** (700, 16px / 24px, -0.005em): section titles inside the report ("Where the detector looked", "Things to check yourself", "Source"), panel titles, and empty-state titles.
- **Body** (400, 16px / 24px): summaries, findings and descriptions, capped at 65ch (60ch for toggle detail, 48ch in empty states).
- **Body Strong** (600, 16px / 24px): buttons, row titles, the confidence line, and values (500 for value cells).
- **Label** (400 or 600, 13px / 19px): metadata, captions under the photo, table headers, the Segmented options, the detector scale legend, and footers.
- **Numeric** (tabular figures): only on numeric cells, such as the confidence line, the register's Confidence column, and the unseen count.

### Named Rules
**The Three Sizes Rule.** There are only three type sizes: 13/19, 16/24 and 28/32. Rank moves through weight (400, 500, 600, 700, 800) and ink (ink vs. muted), never through a new size.

**The Numeric Cells Rule.** Tabular numerals belong on number cells only. Applied to the whole body, `tnum` opens visible gaps around punctuation in Schibsted Grotesk.

## Layout

On desktop (lg, 1024px and up) the shell is a two-column grid: a sticky, full-height 240px UV rail and a workspace. The workspace padding is 40px on the sides, 32px on top and 64px at the bottom. Every page shares one left-aligned column capped at 1180px, so it never centers in a wide window. Below lg, the rail becomes a 56px sticky top bar holding the wordmark and a Settings button, and the four sections (Check, Feed, My Checks, Learn) move to a fixed bottom tab bar. The side padding is then 16px (24px from sm), with 112px of bottom clearance for the tab bar.

The result bench is a container-query layout. At container width @3xl (768px) and up, it splits into two hard halves: the photo on the left on the bench well, and the object label on the right, divided by a 1px rule. Narrower containers stack them photo first, including the browser extension's 360–420px side panel, which reuses the same Results and Analyzing views. Panels in Settings and similar screens use a 260px title column beside the sheet on lg and stack below that.

Spacing runs on a 4px base. Rows are 16px across and 12px tall with a 48px minimum height. Sheet padding is 16px, rising to 24px on wide containers. Sections inside the report are 28px apart, and the label-to-content gap is 8px. Page headers sit 24px (32px on lg) above content. Hit targets are at least 44px.

## Elevation & Depth

The system is flat and tonal. Depth comes from the wall, label and well layers and from 1px rules, not from shadows. Shadows appear in exactly four places, each tied to a physical idea or a state.

### Shadow Vocabulary
- **Object lift** (`box-shadow: 0 1px 2px rgb(0 0 0 / 0.12), 0 8px 24px -8px rgb(0 0 0 / 0.25)`): the photo on the bench, sitting slightly above the well like a print under glass.
- **Dialog** (`box-shadow: 0 18px 48px rgb(0 0 0 / 0.28)`): native modal dialogs, over a backdrop of uv at 55%.
- **Tile hover** (`box-shadow: 0 6px 20px -10px rgb(0 0 0 / 0.3)`): Feed tiles on hover only, together with the border stepping up to rule-strong.
- **Focused mark ring** (`box-shadow: 0 0 0 4px var(--glow)`): a mark on the photo when its note is hovered or focused, under detector light.

### Named Rules
**The Flat Sheet Rule.** Sheets, panels, registers and rows never cast shadows at rest. If something needs to separate, give it a 1px rule or a tonal step, not elevation.

## Shapes

Corners are nearly square, like cut card stock. Sheets (results, panels, the register, empty states, dialogs, the demo notice, and the error banner) use a 3px radius. Controls (buttons, the link field, the search input, rail links, and Segmented options) use a soft 6px radius. The Segmented track is 8px, so the 6px option sits inside it with 4px of padding. Circles are kept for things that are objects in themselves: verdict marks, numbered pins and note rings, the toggle, avatars, the detector scale, and the status dot.

Borders are 1px hairlines, with 1.5px for numbered note rings, pins and the dashed drop frame. Photos are never cropped on the bench. Instead, registration crop marks frame them: four 14px corner brackets, 1px, set 10px outside the image. They are rule-strong in plain light and turn glow under detector light. The same marks frame the idle drop target. Feed previews are the one place images are cropped (4:3), so the grid aligns.

## Components

### Buttons
Plain, firm and squared off. Every variant has a 1px border, 6px radius, semibold 16px text, a 44px minimum height, 10px × 16px padding, an optional 18px leading icon, and 150ms color transitions.
- **Primary:** uv fill and border with on-uv text, hovering to uv-active. In dark mode it is filled with the accent lavender, with wall-colored text.
- **Secondary:** label fill with a rule-strong border and ink text, hovering to well.
- **Quiet:** transparent border and accent text, hovering to a well fill.
- **Danger:** label fill with a rule-strong border and ai text, hovering to ai-wash. Used for Clear all and confirm-delete.
- **Disabled:** well fill, rule border, muted text, default cursor.

### Chips (Segmented)
- **Style:** an 8px-radius label track with a 1px rule border and 4px padding. Options are 36px tall, 13px semibold, with 14px horizontal padding.
- **State:** the active option is a uv fill with on-uv text (accent with wall text in dark mode). Inactive options are muted text that hovers to ink on well. This same control is the Plain light / Detector light switch and the My Checks verdict filter (All, Real, Edited, AI).

### Cards / Containers
- **Corner Style:** 3px.
- **Background:** label stock on the wall. The bench's photo half and the drop frame use well.
- **Shadow Strategy:** none at rest (see the Flat Sheet Rule). Feed tiles alone lift on hover.
- **Border:** 1px rule. Internal sections are separated by 1px rules, never by nested cards.
- **Internal Padding:** 16px, or 24px in wide containers. Rows are 16 × 12px.

### Inputs / Fields
- **Style:** the link field is a label fill with a 1px rule-strong border and 6px radius. It is 56px tall when idle (48px in the results bar), with a leading 18px link icon in muted and the Check button inside its right edge. Search uses a rule border and is 44px tall.
- **Focus:** the border shifts to accent, with a 2px accent outline at 25% around the field. Everywhere else, the focus outline is 2px solid accent with a 2px offset.
- **Error:** a 3px sheet in ai-wash with an ai/40 border. A semibold ai lead-in ("Couldn't check this image.") is followed by plain text and a dismiss button.

### Navigation
- **Desktop rail:** uv background, 240px wide, padded 24px × 16px. It starts with the wordmark lockup (a 22px framed patch-grid glyph with one glow cell, next to "WildcatVerify" in 800 weight). Below that come the four section links (44px, 6px radius, 18px icons), then the rail foot: a detector status block in a 1px on-uv/15 frame (the glow dot plus "Detector ready", model name, privacy line) and Settings. Hover is uv-active at 60%. The active item is white on uv-active (see the White-on-Active Rule).
- **Mobile:** a 56px uv top bar with the wordmark and a 44px Settings icon button. A fixed bottom tab bar holds the four sections with a 22px icon over the label, in label at 95% with a backdrop blur and a top rule. The active tab is accent in bold with a heavier icon stroke, and inactive tabs are muted.

### Verdict Mark
One filled disc with a white-label glyph (check for Real, sparkles for AI, warning triangle for Edited), drawn at three sizes: 48px on the object label, 36px for thumbnails and fallbacks, and 24px in tags. Tags pair the 24px mark with the full verdict word in semibold verdict ink.

### Object Label (signature)
This is the right half of the bench, set like a museum object label on plain label stock. It opens with a 13px muted line (exact check time on the left, source on the right). Next comes the 48px verdict mark beside the title-size verdict in its ink, with "NN% confidence" in tabular semibold underneath. Below that is the **detector scale**: a 6px rounded track from Real to AI, at most 420px wide, with a 1px ink/60 tick at 50% and a 14px verdict-colored marker (with a 2px label ring) at the AI probability. It's labeled "Real · AI at 50% · AI" in 13px muted. A rule separates this from the notes: summary, quoted caption, "Where the detector looked" (numbered 32px accent rings with Show), "Things to check yourself" as ruled checkboxes, What to do, Source rows, then Share result (primary) and Check another (secondary).

### Plain light / Detector light (signature)
This is the photo half of the bench: the whole photo in crop marks, with the object lift shadow, on the well. Plain light leaves the photo untouched. Detector light runs a 500ms expo-out transition that grayscales and darkens the photo (brightness 0.55, contrast 1.1) and lays uv over it in multiply at 80%. It then draws the 24×24 patch map as crisp, pixelated glow cells (opacity rising with strength, faint cells dropped) and places numbered pins sized by rank (40, 34, 28px; label fill with a uv ring, or glow fill in dark mode). Hovering or focusing a note draws a 1px glow leader line from the note's number to its pin, measured live from layout.

## Do's and Don'ts

### Do:
- **Do** put each result on one label-stock sheet (3px radius, 1px rule), with ruled rows inside it.
- **Do** carry rank with weight (400–800) and ink vs. muted inside the three sizes: 13/19, 16/24, 28/32.
- **Do** pair every verdict ink with its filled mark and its full "Likely …" word. Short forms are for the verdict filter only.
- **Do** frame photos whole with registration crop marks on the bench, and frame the idle drop target the same way.
- **Do** keep every page in the shared left-aligned column, max 1180px.
- **Do** use tabular numerals only on numeric cells.
- **Do** give controls a 6px radius and sheets a 3px radius.

### Don't:
- **Don't** use glow outside detector light, except for the detector-ready dot and the wordmark's lit cell.
- **Don't** tint, filter or crop the photo in plain light.
- **Don't** add a fourth type size or set tabular numerals across the body.
- **Don't** stack floating cards or add shadows to sheets at rest.
- **Don't** show a verdict by color alone, and don't show Likely Edited as a detector outcome.
- **Don't** center pages in wide windows or widen the column past 1180px.
