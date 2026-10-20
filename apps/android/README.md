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
  Close other heavy jobs (model exports, Xcode builds) while it runs; on a 16 GB Mac the
  emulator hangs and quits when memory runs out.
- **Detector**: runs on the CPU with XNNPACK (the emulator has no GPU delegate support).
  One check is ~1.3–1.5 s on a 6-core emulator; real phones are usually faster. The model is
  warmed up once in the background after launch, so the first check isn't the slow one.
  `DetectorBenchmark` (androidTest) logs each stage: `adb logcat -s DetectorBenchmark`.
- **Smaller/faster model (optional)**: `ml/scripts/export/quantize_tflite.py` makes an int8
  version (23 MB, ~35% faster on CPU, same decisions on 120 test images), but its heatmaps are
  noticeably noisier, so the app ships the float model to match iOS.

## Detector

`app/src/main/assets/wildcat_detector.tflite` is the CommunityForensics ViT + rich probe,
exported with `ml/scripts/export/community_forensics_vit_heatmap_tflite.py` (outputs
`fake_prob` and the 24×24 `patch_map`; verified against PyTorch). `DetectorPreprocessor`
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
- Not ported (iOS-only): Control Center/Lock Screen controls, Visual Intelligence, Siri.

## Builds

| Flavor | For | Labels in Bluesky |
|---|---|---|
| `play` | Google Play | Feed tab labels, plus the screen-capture **label tab** |
| `sideload` (`.sideload` app id) | Direct install / F-Droid | Also the accessibility **Auto-Label** (Play restricts accessibility services to accessibility tools) |

Each has `debug`, `fast` (optimized, debug-signed) and `release`: e.g. `./gradlew :app:assemblePlayFast`.

## Labels

- **Feed tab** (`FeedLabeler`): labels each post's full-size photo as it scrolls into view,
  visible posts first, one at a time. Optional Bluesky sign-in (app password,
  `com.atproto.server.createSession`) adds the Following timeline; tokens are encrypted with an
  Android Keystore key (`SessionVault`).
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
| Siri "Check This Post" / "Check the copied link" | Removed: Feed labels and the label tab label photos without leaving the feed |
| UserDefaults / Application Support | SharedPreferences / `noBackupFilesDir/History` |
