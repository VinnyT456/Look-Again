# WildcatVerify (Android)

Kotlin + Jetpack Compose port of `apps/ios/WildcatVerify` (minSdk 28, target 37).
Same tabs (Feed · Learn · Check · My Checks · Settings), same copy, same detector.

## Build

```bash
cd apps/android
scripts/copy_model.sh          # copies the detector from ml/checkpoints/tflite into assets
./gradlew :app:assemblePlayDebug
./gradlew :app:testPlayDebugUnitTest           # JVM tests
./gradlew :app:connectedPlayDebugAndroidTest   # runs the real model on a device/emulator
```

## Speed

- **Use the `fast` build for trying the app**: `./gradlew :app:assemblePlayFast` then
  `adb install -r app/build/outputs/apk/play/fast/app-play-fast.apk`. It is R8-optimized and not
  debuggable (debug builds run Compose and Kotlin loops several times slower). Cold start on
  the emulator: ~0.7 s vs ~2.6 s for debug. It installs beside the debug app as `….fast`.
- **Emulator**: give the AVD 6 cores and 4 GB (Device Manager → Edit → Advanced, or
  `hw.cpu.ncore=6`, `hw.ramSize=4096`, `hw.gpu.mode=host` in its `config.ini`). The default
  "Medium Phone" AVD had 1 core, which made every check 5–10× slower. Keep Quick Boot on.
  Close other heavy jobs (model exports, Xcode builds, Gradle builds) while it runs; on a 16 GB
  Mac the emulator hangs and quits when memory runs out.
- **Detector**: runs on the CPU with XNNPACK (the emulator has no GPU delegate support).
  One check is ~1.3–1.5 s on a 6-core emulator; real phones are usually faster. The model is
  warmed up once in the background after launch, so the first check isn't the slow one.
  `DetectorBenchmark` (androidTest) logs each stage: `adb logcat -s DetectorBenchmark`.
- **Smaller/faster model (optional)**: `ml/scripts/export/quantize_tflite.py` makes an int8
  version (23 MB, ~35% faster on CPU, same decisions on 120 test images), but its heatmaps are
  noticeably noisier, so the app ships the float model to match iOS.

## Detector

`app/src/main/assets/wildcat_detector.tflite` is the CommunityForensics ViT + rich probe,
using the `genai_plus_balance` fine-tuned probe (same weights as iOS), exported with
`ml/scripts/export/community_forensics_vit_heatmap_tflite.py --weights …` (outputs `fake_prob`
and the 24×24 `patch_map`). `DetectorModelTest` checks both against PyTorch
(`androidTest/assets/fixtures/torch_reference.json`): probabilities within 1e-4, heatmap
correlation > 0.99. The iOS reference isn't used for heatmaps: Core ML's fp16 maps drift from
PyTorch (correlation ~0.6). `DetectorPreprocessor`
reimplements PIL's antialiased bicubic resize, so preprocessing matches Python's channel means
within 0.002. If the model fails to load, the labelled demo classifier is used.

## Ported from iOS (October 2026 update)

- **Look Again** practice on the Learn tab: 4 answers (adds "False story"), balanced rounds that
  avoid the last round's cases, best score, progress dots, mascot reactions, review of misses,
  and a link to the clue group you missed most. Cases are in `model/PracticeBank.kt`
  (generated from the iOS bank; image cases take an `imageRes` and optional `hotspots`).
- **Clue Guide** with a group switcher and an index on the Learn tab.
- **Multi-image posts**: every image is checked; the most suspicious leads, with a strip to switch.
- **Content Credentials (C2PA)** read from uploaded/shared JPEG and PNG files
  (`ContentCredentialsReader`; signatures aren't verified).
- **Feed ••• menu**: hide a post, hide an account (Settings → Hidden Accounts), report.
- **Terms of Use** ([TERMS.md](TERMS.md)) and privacy updates ([PRIVACY.md](PRIVACY.md)).
- **Feed auto-check**: posts are checked as they scroll into view; a verdict line (badge, %,
  Details) waits under each one. Paused in Battery Saver and on metered networks or Data Saver
  (`DeviceConditions`); toggle in Settings → Feed.
- **Copied-link offer** on the Check tab: when the clipboard probably holds a link, a card offers
  to check it. Only the clip's description is read until you tap (`ClipboardProbe`).
- **Answer-first results**: verdict, photo and credentials first; findings, what to do and the
  source sit behind "Why This Verdict?".
- **Ways to Check**: shown on first launch and in Settings.
- Not ported (iOS-only): Action extension (Share already covers it), Control Center/Lock Screen
  controls, Visual Intelligence, Siri.

## Builds

| Flavor | For | Labels in Bluesky |
|---|---|---|
| `play` | Google Play | Feed tab labels, plus the screen-capture **label tab** |
| `sideload` (`.sideload` app id) | Direct install / F-Droid | Also the accessibility **Auto-Label** (Play restricts accessibility services to accessibility tools) |

Each has `debug`, `fast` (optimized, debug-signed) and `release`: e.g. `./gradlew :app:assemblePlayFast`.

## Labels

- **Feed tab** (`FeedAutoChecker`): checks each post's thumbnail as it scrolls into view,
  visible posts first, one at a time; posts that scroll away are dropped from the queue. Optional Bluesky sign-in adds the Following timeline.
- **Sign-in** (`BlueskyOAuth.kt`, `BlueskyAccount`, `BrowserSignIn`): AT Protocol OAuth, the same
  client as iOS (`docs/oauth-client-metadata.json`): PAR with PKCE, DPoP-bound tokens (P-256 key
  per session), Bluesky's page in a Custom Tab, and the redirect `io.github.vinnyt456:/oauth/callback`
  back to `MainActivity`. "Account on Another Server…" signs in through that account's own server.
  The session is encrypted with an Android Keystore key (`SessionVault`).
- **Label tab** (`ScreenLabelService` + `FloatingTab`): MediaProjection screen capture at half
  resolution (user consent each session; Android 14+ can share only Bluesky), a draggable tab over
  other apps, and badges. Photos are found from pixels (`PixelPhotoFinder`). Big frame-to-frame
  changes count as scrolling and hide badges; small ones (videos, our own badges) don't.
- **Auto-Label** (`sideload` only, `AutoLabelService`): photo bounds from the accessibility tree,
  one accessibility screenshot per settled screen.
- Both on-screen modes share `PhotoLabeler` (hash cache, one check at a time, tap → result) and
  `BadgeOverlay`.

## iOS → Android mapping

| iOS | Android |
|---|---|
| Share extension | Share → **WildcatVerify** (`ShareActivity`, memory only, Done discards) |
| Siri "Check This Post" | Removed: Feed auto-check and the label tab label photos without leaving the feed |
| Siri "Check the copied link" | Copied-link card on the Check tab |
| `ASWebAuthenticationSession` sign-in | Custom Tab + redirect intent filter |
| Keychain | Keystore-encrypted SharedPreferences |
| UserDefaults / Application Support | SharedPreferences / `noBackupFilesDir/History` |
