# WildcatVerify (iOS)

SwiftUI app (iPhone, iOS 18+, Swift 6) for checking whether a Bluesky photo is real,
edited or AI-generated.

## Build and test

The Xcode project is generated from `project.yml` with [XcodeGen](https://github.com/yonaskolb/XcodeGen):

```bash
cd apps/ios/WildcatVerify
xcodegen generate
open WildcatVerify.xcodeproj
```

Run everything with ⌘U, or:

```bash
xcodebuild test -scheme WildcatVerify -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

- `WildcatVerifyTests/` (Swift Testing, 97 tests): Bluesky link parsing and every API failure
  mode against a stubbed `URLSession` (404/500, bad JSON, deleted post, text-only post,
  offline, timeout, cancel); image download, caching and downsampling; the check flow end to
  end; cancel and reset; search, filters, delete and clear in My Checks; tab badge and
  navigation; demo labelling.
- `WildcatVerifyUITests/` (XCTest, 14 tests): real taps through the app — tabs, a full
  Look Again round, the Clue Guide, link
  validation, the invalid-link alert, photo picker, opening an example, Check Another Image,
  empty My Checks, About and the privacy policy, plus launches at the largest text size and
  in dark mode.

## Architecture (MVVM)

```text
WildcatVerify/
├── App/          @main entry
├── Models/       VerdictType, VerificationCase, HotspotArea, SampleData, …  (one type per file)
├── Services/     BlueskyService (public AppView), ImageClassifying + DemoImageClassifier,
│                 ImageRepository (off-main downsampling), HistoryStore
├── ViewModels/   AppViewModel (tabs), CheckViewModel, CheckResultsViewModel,
│                 LearnViewModel, PracticeViewModel, HistoryViewModel
├── Intents/      App Intents for Siri and Shortcuts (Check Image, Check Copied Link,
│                 Open Check), the Siri card, and the App Shortcuts phrases
├── Views/        Root, Check, Screenshot (box screen), Results, Feed, Learn, History,
│                 Settings, Siri, About, Shared
├── Theme/        Metrics (sizes, radii)
└── Resources/    Assets (colors with light/dark/Increase Contrast variants, logo, app icon),
                  PrivacyInfo.xcprivacy
```

- Native `TabView` with the `Tab` API; each tab owns a `NavigationStack` with
  value-based `navigationDestination(for:)`.
- Screens are inset-grouped `List`s; brand lives in the logo, the purple tint and the
  verdict colours. Colors come from the asset catalog via generated symbols
  (`Color.verdictAI`, `Image(.faceCheckMagnifier)`).
- Results show the whole photo (aspect-fit, never cropped). The highlight box is
  placed by `NormalizedRectLayout`, a custom `Layout` that maps the model's 0–1
  hotspot onto the drawn image.
- Motion lives in `Theme/Motion.swift`: tab switches slide in from the side you moved toward
  (`TabEntrance`) with a selection haptic; the Check card and recent list fade up with a
  40 ms stagger (`StaggeredAppear`); the photo drop zone dips on press. Reduce Motion turns
  all of it into plain fades.
- Supports Dynamic Type through the accessibility sizes, VoiceOver announcements,
  Reduce Motion, Increase Contrast, dark mode, and portrait + landscape.

## Detection model

`Resources/Models/WildcatDetector.mlpackage` (42 MB) is the CommunityForensics ViT +
rich-feature linear probe exported from `ml/` (`ml/checkpoints/coreml/community_forensics_vit_rich_probe`,
script `ml/src/look_again/community_forensics_vit_probe.py`; metadata in `Design/WildcatDetector.json`).

- **Input:** 1×3×384×384 Float32. `DetectorPreprocessor` mirrors the model's `CLIPImageProcessor`:
  short edge → 440, center-crop 384, ÷255, normalize with CLIP mean/std. Horizontal-flip TTA
  and the sigmoid are inside the model.
- **Outputs:** `fake_prob`, and `patch_map` (1×24×24). `CoreMLImageClassifier` maps ≥ 0.5 →
  **Likely AI**, otherwise **Likely Real**; confidence is the winning side's probability, shown
  capped at 99%.
- **Heatmap:** `patch_map` is each 16 px patch's exact share of the patch-feature part of the
  logit (≈72% of the probe's weight; the rest is whole-image features with no location).
  Highlight draws it (yellow → red) over the center crop the model saw, only for **Likely AI**,
  labelled "Red areas influenced the detector most". It shows what swayed the detector, not
  proof of an edit.
- **What it can't do:** it's binary, so it never says **Likely Edited**. Findings read "Things to
  check yourself" rather than claiming evidence the model didn't report.
- **Verified:** `DetectorTests` compares the app's preprocessing and probabilities with the
  Python pipeline on fixtures (`WildcatVerifyTests/Fixtures`, `reference.json`).
- **Updating:** run `ml/scripts/export/community_forensics_vit_heatmap_coreml.py` (rebuilds from
  the saved probe weights, checks the decision is unchanged and the heatmap decomposition is
  exact, then verifies Core ML against PyTorch), copy the `.mlpackage` here as
  `WildcatDetector.mlpackage`, regenerate `reference.json` (incl. `patch_map`) with the same
  fixtures, and rerun the tests.
- `ClassifierFactory` loads the model once per process; if loading ever fails it falls back to
  `DemoImageClassifier`, whose results are labelled "Demo result".

The model ships only in the app. The share extension loads it from its containing app bundle.
Share extensions are capped at roughly 120 MB of memory; the model ran in the Simulator (which
doesn't enforce the cap) but still needs a check on a real iPhone.

Logo assets (sizes, dark variant, dark/tinted app icons) are generated from
`Design/FaceCheckMagnifier-master.png` by `Design/make_logo_assets.py`; color sets by
`Design/make_colorsets.py`.

## Tabs

**Feed · Learn · Check · My Checks · Settings** (Check in the middle).

- **Feed** — image posts from Bluesky's public What's Hot feed (`BlueskyFeedService`,
  `app.bsky.feed.getFeed`, no sign-in). Posts or authors with any moderation/self label are
  skipped. Tap a post to check its first image; the result goes to My Checks.
- **Learn** — Look Again practice (played in place) and the Clue Guide.
- **Check** — paste a link or choose a photo.
- **My Checks** — search, filter by verdict, swipe to delete.
- **Settings** — Keep My Checks (off by default), Haptics, Show Heatmap, detector facts,
  privacy policy, Erase All Data. Stored in `UserDefaults` via `SettingsStore`.

### Keep My Checks (opt-in)

Off: history lives in memory and clears when the app closes. On: `HistoryPersistence` writes
`Application Support/History/history.json` plus ≤1024 px JPEG copies of uploaded/shared photos
(Bluesky photos are re-fetched from Bluesky instead). Complete file protection, excluded from
backups. Turning it off, clearing My Checks, or Erase All Data deletes the folder.

## Share extension

`WildcatVerifyShare` adds **WildcatVerify** to the system share sheet. It accepts one image,
a Bluesky post URL, or text containing a Bluesky link (`ShareItemLoader` prefers the image),
runs the same `CheckPipeline` as the app, and shows the same Results screen. Tapping Done
discards everything; nothing is written to disk.

Shared code compiled into both targets: `Models/`, `Services/`, `Share/`, `Theme/`,
`Views/Shared/`, `Views/Results/`, `AnalyzingView`, `CheckResultsViewModel`, `PhotoLayer`.
Extension-only differences use the `SHARE_EXTENSION` compilation condition (no "Open on
Bluesky" or nested share sheet, since extensions can't open other apps).

Share extensions are limited to about **120 MB** of memory. A
full-precision ViT-B (~340 MB) won't fit; a quantized/palettized Core ML export may. If it
doesn't fit, keep the extension light and hand off instead: add an App Group, have the
extension save the shared item to the group container, and let the app pick it up when it
opens. That stores the item on disk until the app runs, so the privacy policy would need
a matching update.

## Siri and Shortcuts

Apps can't see what's on screen in Bluesky, so Siri is the hand-off. Nothing needs Photos
access.

- **Check This Post** (the main flow): a user-made shortcut, *Take Screenshot → Check Image
  with WildcatVerify*. `CheckImageIntent` takes the image as an `IntentFile`, opens the app
  and calls `AppViewModel.live.receiveScreenshot`. `ScreenshotCropScreen` shows it full
  screen with a box `PhotoAreaFinder` suggests (Vision rectangles, then attention saliency,
  then a centred box). The user drags the box or its corners (`CropBox`, 0–1 coordinates),
  and only the boxed pixels (`ImageCropper`) go through `CheckPipeline`. The result opens on
  the Check tab and lands in My Checks.
- **Check the copied link** (App Shortcut, works with no setup): `CheckCopiedLinkIntent` reads
  a Bluesky link from `UIPasteboard` (iOS shows its paste prompt), checks it in the
  background, records it, and answers with `CheckSnippetView`: thumbnail, verdict,
  confidence and an **Open** button (`OpenCheckIntent`, hidden from Shortcuts).
- **Settings → Siri & Shortcuts** (`SiriSetupView`) explains both, plus Action Button and
  Back Tap. The Check page shows a dismissible tip that leads there.

- **Controls** (`WildcatVerifyControls`, iOS 18): Control Center / Lock Screen / Action Button
  buttons for Check Copied Link and Check a Post. They only open `wildcatverify://` links
  (`AppDeepLink`); the app accepts those two fixed actions and nothing else.
- **Visual Intelligence** (iOS 26, Apple Intelligence iPhones): `VisualCheckQuery` answers image
  searches with "Check with WildcatVerify"; tapping it runs `OpenVisualCheckIntent`, which opens
  the box screen with that image. The framework is device-only, so the code is behind
  `#if canImport(VisualIntelligence)` and doesn't run in the Simulator.
- **Every image in a post** is checked; the most suspicious one leads and the Results screen
  shows all of them (`PostImageStrip`).
- **Content Credentials** (`ContentCredentialsReader`): C2PA manifests in JPEG/PNG uploads are
  read on device (generator, AI source type, edit history) and shown in Results. Signatures
  aren't verified, and the UI says so. Bluesky strips them, so this only shows for photos from
  the library or the share sheet.

**One-tap install.** Build the shortcut on an iPhone, then in Shortcuts long-press it →
Share → **Copy iCloud Link**, and paste the link into `AppLinks.checkThisPostShortcut`. Set Up
Siri then shows an **Add "Check This Post" Shortcut** button above the manual steps.

## Sign in with Bluesky (optional, off until published)

`Account/` holds the AT Protocol OAuth client for native apps: handle/DID resolution, PAR with
PKCE (S256), DPoP (ES256, per-session key, nonce retry), token refresh (one at a time; refresh
tokens are single-use), and a Keychain-backed `BlueskyAccount`. It feeds the Feed tab's
**Following** timeline (`TimelineFeedService`, `app.bsky.feed.getTimeline` through the user's own
server with `atproto-proxy`). Tokens stay in the Keychain on this device; a fresh install
discards any leftover sign-in (`discardLeftoverSignIn`).

Bluesky rejects sign-ins (`invalid_client_metadata`) until the client file is public:
1. Host `docs/` on Vercel (Root Directory `docs`); it is live at
   `https://look-again-beta.vercel.app/`.
2. Check `https://look-again-beta.vercel.app/oauth-client-metadata.json` loads with no login or redirect.
3. Set `BlueskyOAuthConfig.isSignInAvailable = true` and rebuild.

If the address changes, change `clientID`, `callbackScheme` (the host reversed) and the
matching fields in `docs/oauth-client-metadata.json`; a test checks they agree.

## Fewer taps

- **Copied link offer**: on open, `CheckViewModel.refreshCopiedLinkOffer()` asks iOS whether the
  clipboard *looks like* a link (`detectedPatterns`, no prompt). If so, "Check the link you
  copied" shows a system `PasteButton` (no prompt), and pasting a Bluesky link checks it at once.
  Pasting into the field does the same.
- **Answer-first results**: verdict, confidence and summary lead; findings, what to do and source
  sit behind "Why This Verdict?".
- **Feed auto-check** (`FeedAutoChecker`, Settings → Feed, on by default): classifies each post's
  thumbnail as it scrolls in, one at a time, and shows a verdict badge. Pauses in Low Power Mode
  and Low Data Mode (`NetworkConditions`); the Feed shows a banner saying why. Cellular alone doesn't pause it, since the Feed has already downloaded each thumbnail. When a pause ends, posts on screen are checked without scrolling (`FeedAutoChecker.resume()`). Opening a post runs the full check.
- **Check with WildcatVerify** (`WildcatVerifyAction`, `com.apple.ui-services`): an action in the
  share menu's action list, so press-and-hold → Share on any image in Bluesky, Safari, Photos or
  Messages checks it. Same code as the share extension.
- **Auto-box**: Siri screenshots skip the box screen when Vision's rectangle confidence is ≥ 0.9
  (`PhotoAreaFinder.confidentPhoto`); the result offers "Adjust the Checked Area".
- **Ways to Check**: one skippable screen on first launch, also under Settings.

## Learn tab

- **Look Again**: played in place on the Learn home. Each case is drawn as a Bluesky post
  (monogram avatar, name, `.example` handle, caption, and a plain description of the photo that
  doesn't name the giveaway). Answers stay neutral until you pick; then the correct answer and
  your pick are marked, with the explanation and clues below. Dots use shape (filled vs. slashed)
  as well as color. The end card lists misses and links to the clue group you missed most.
- **Clue Guide**: three groups (AI, editing, source) with 2026-era clues and a Bluesky source
  group (labels, first post, replies, alt text, Content Credentials). The AI verdict icon is
  `cpu` app-wide.

Practice questions are written scenarios for now. To add an image question, drop the image
into `Assets.xcassets` and add a `PracticeQuestion` with `imageName` set; the question card
shows it above the prompt. Only use images you have the rights to ship. The bank tests
require unique ids, every verdict represented, at least 3 questions per verdict, and a
written explanation for each.

## Credits

The detector is built on **CommunityForensics-DeepfakeDet-ViT**
([Hugging Face](https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT)),
from *Community Forensics: Using Thousands of Generators to Train Fake Image Detectors*
by Jeongsoo Park and Andrew Owens, CVPR 2025
([paper](https://arxiv.org/abs/2411.04125), [code](https://github.com/JeongsooP/Community-Forensics)).
Hugging Face conversion by Han Yoon, Borderless / Ethix R&D. MIT License: the full notice
ships in the app (`Resources/Licenses/community-forensics-vit-MIT.txt`, shown under
Settings → Credits and About → Credits) and is kept in `ml/docs/licenses/`. The linear probe
and patch heatmap on top are this project's.

```bibtex
@InProceedings{Park_2025_CVPR,
    author    = {Park, Jeongsoo and Owens, Andrew},
    title     = {Community Forensics: Using Thousands of Generators to Train Fake Image Detectors},
    booktitle = {Proceedings of the Computer Vision and Pattern Recognition Conference (CVPR)},
    month     = {June},
    year      = {2025},
    pages     = {8245-8257}
}
```

## Privacy and App Store checklist

The full rules guide (privacy, user-generated content, trademarks, metadata, and what is
still an App Store Connect step) is in [COMPLIANCE.md](COMPLIANCE.md). Terms of Use are in
[TERMS.md](TERMS.md) and in the app under Settings → Terms of Use.

| Requirement | Status |
|---|---|
| Privacy manifest (`PrivacyInfo.xcprivacy`) | App and extension. No tracking, no collected data types. Declares `NSPrivacyAccessedAPICategoryUserDefaults` / `CA92.1` for the app's own settings. |
| Privacy policy in app (Guideline 5.1.1(i)) | About → Privacy Policy, bundled so it works offline. |
| Privacy policy URL in App Store Connect | `PRIVACY.md`. The GitHub link in `AppLinks.privacyPolicy` only works if the repository is public; otherwise host the file (e.g. GitHub Pages) and update both places. |
| App Privacy label | **Data Not Collected.** Photos are processed on device; Bluesky links and the Feed are fetched directly from Bluesky; the opt-in history stays on the device (on-device storage isn't "collection"). Nothing reaches the developer. |
| Photo access permission string | Not needed: `PhotosPicker` runs out of process and only returns the photo the user picks; Siri's Check Image gets the screenshot from the shortcut, not the library. Add `NSPhotoLibraryUsageDescription` only if the app ever reads the library directly. |
| Tracking (ATT) | Not applicable: no tracking, no `NSUserTrackingUsageDescription`. |
| Account deletion (5.1.1(v)) | Not applicable: no accounts. |
| Export compliance | `ITSAppUsesNonExemptEncryption = NO` (HTTPS and CryptoKit hashing only). |
| App Transport Security | All requests are HTTPS; no exceptions. |
