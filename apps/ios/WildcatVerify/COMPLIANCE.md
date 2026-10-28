# App Store Rules and Privacy Checklist

What Apple (and privacy law) expects from an iOS app like WildcatVerify, and where the app
stands. ✅ done in the app · ⚠️ needs a decision or an App Store Connect step · ➖ doesn't apply.

This is a working checklist, not legal advice. Guideline numbers refer to Apple's
[App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/).

## 1. Privacy (Guideline 5.1)

| Rule | What it means | Status |
|---|---|---|
| Privacy policy (5.1.1(i)) | A policy reachable in the app **and** at a public URL entered in App Store Connect. | ✅ In app (Settings and About → Privacy Policy) and `PRIVACY.md`. ⚠️ The GitHub link only works if the repo is public; otherwise host it (e.g. GitHub Pages) and update `AppLinks.privacyPolicy`. |
| Ask before accessing protected data (5.1.1(ii)) | Every protected resource needs an Info.plist purpose string and a system prompt. | ✅ None needed: `PhotosPicker` and Shortcuts hand over only what the user picks, the clipboard is read through `PasteButton` or iOS's paste prompt. Add a purpose string if you ever use the camera, the full photo library, location, contacts or the microphone. |
| Data minimization (5.1.1(iii)) | Only ask for what the feature needs. | ✅ No account, no library access, metadata dropped on decode, history opt-in. |
| Account deletion (5.1.1(v)) | Apps with sign-up must offer in-app account deletion. | ➖ No accounts. Settings → Erase All Data covers local data. |
| Optional Bluesky sign-in (4.8, 5.1.1(v)) | Third-party login for a primary account needs an equivalent privacy-focused option (Sign in with Apple) unless the app is a client for that service. | ⚠️ WildcatVerify has no accounts of its own; Bluesky sign-in only unlocks reading the user's own timeline, which fits the "client for a specific third-party service" exemption. Confirm with App Review notes. Sign-out and Erase All Data remove it; tokens live in the Keychain and are discarded on a fresh install. |
| Hosted OAuth client file | A public `oauth-client-metadata.json` must exist at the client ID URL. | ⚠️ Publish `docs/` with GitHub Pages, then set `BlueskyOAuthConfig.isSignInAvailable = true`. |
| Third-party AI disclosure (5.1.2(i)) | Personal data sent to a third-party AI service must be disclosed and agreed to first. | ✅ All analysis is on device (Core ML). Stated in the privacy policy. |
| Tracking / ATT (5.1.2) | Tracking across apps needs the App Tracking Transparency prompt. | ➖ No tracking, no ads, no analytics SDKs. |
| App Privacy label | The "nutrition label" in App Store Connect must match reality. | ⚠️ Answer **Data Not Collected**. Re-check it whenever a feature sends data anywhere (crash reporting, analytics, a hosted model). |
| Privacy manifest | `PrivacyInfo.xcprivacy` declares tracking, collected data and "required reason" APIs. | ✅ App and share extension: no tracking, no collected data, UserDefaults with reason `CA92.1`. Add an entry if you start using file timestamps, disk space, system boot time or active keyboards APIs, and include manifests from any SDK you add. |
| Children (5.1.4, COPPA) | Kids category apps have strict rules; all apps must not knowingly collect children's data. | ✅ Not in the Kids category; policy has a children section. |
| GDPR / CCPA rights | People can ask what data you hold and have it deleted. | ✅ Everything is on device and erasable; policy explains rights and how to contact you. |

## 2. Safety and user-generated content (Guideline 1)

| Rule | What it means | Status |
|---|---|---|
| UGC moderation (1.2) | Apps showing other people's posts need a way to filter objectionable content, **report** it, **block** abusive users, and published contact info. | ✅ Feed hides any post or author with a Bluesky content label; ••• on each post offers Hide This Post, Hide Posts from @account (managed in Settings → Hidden Accounts), Report on Bluesky, and Report to WildcatVerify. ⚠️ A support **email** is stronger than a GitHub link for reports; add one to `AppLinks.support` if you ship. |
| Accuracy and harm (1.1, 1.4) | Don't present guesses as facts in ways that could hurt people. | ✅ Every result says "a verdict is an estimate, not proof"; shared results say the same; demo verdicts are always labelled; confidence is capped at 99%. ⚠️ Keep the App Store description honest too (no "detects every fake"). |
| Age rating | Questionnaire in App Store Connect (4+, 9+, 13+, 16+, 18+). | ⚠️ Answer **yes** to user-generated content. Expect 13+ or higher because of the live Bluesky feed. |

## 3. Legal and intellectual property (Guideline 5.2, 5.3)

| Rule | What it means | Status |
|---|---|---|
| Others' trademarks (5.2.1) | You need permission to use another organization's names, logos or colors in a way that suggests affiliation. | ⚠️ **"Wildcat", Northwestern Purple and the `edu.northwestern` bundle ID** point at Northwestern University. Get written permission from the university (brand/licensing office) or rename and change the bundle ID before shipping. |
| Third-party services (5.2.2) | Use services within their terms and don't imply endorsement. | ✅ Uses Bluesky's public API; Terms say WildcatVerify isn't affiliated with Bluesky; no Bluesky logo in the app. |
| Open source licenses | Keep license notices for code or models you ship. | ✅ CommunityForensics ViT (MIT) notice in Settings → Credits and bundled. |
| Terms / EULA | Apple's standard EULA applies unless you provide your own. | ✅ Standard EULA plus `TERMS.md` / Settings → Terms of Use (fair use, estimates, no warranty). |
| Siri / Apple trademarks | Don't use "Siri" or Apple marks in the app name or icon. | ✅ Name and icon are clean; "Siri & Shortcuts" is only used as a feature label. |

## 4. App completeness and metadata (Guidelines 2, 4)

| Rule | What it means | Status |
|---|---|---|
| No placeholders (2.1) | Reviewers reject demo content and unfinished features. | ✅ Shipped build includes the detection model. ⚠️ Confirm on a device that `DemoImageClassifier` never runs (Settings → Detector shows "CommunityForensics ViT"). |
| Stability (2.1) | No crashes during review. | ⚠️ Test the share extension on a real device: extensions get roughly 120 MB of memory and the model is 42 MB. |
| Accurate metadata (2.3) | Screenshots and description show the real app. | ⚠️ App Store Connect step. |
| Review notes | Tell the reviewer how to try features that need setup. | ⚠️ Explain: no login; Siri "Check This Post" needs the shortcut (link in Settings → Siri & Shortcuts); "Check the copied link" works after copying a Bluesky post link. |
| Support URL | Required in App Store Connect. | ⚠️ Use the GitHub issues page or a simple support page. |
| Accessibility Nutrition Labels | Declare which accessibility features the app supports. | ⚠️ App Store Connect step. The app supports VoiceOver, Larger Text, Dark Interface, Differentiate Without Color, Sufficient Contrast and Reduced Motion. |
| Export compliance | Declare encryption use. | ✅ `ITSAppUsesNonExemptEncryption = NO` (HTTPS only). |
| EU Digital Services Act | Publishing in the EU requires declaring trader status. | ⚠️ App Store Connect step. A trader's contact details are shown publicly; a non-commercial student project can usually declare non-trader. |

## 5. Habits to keep while building

- Every new feature that touches user data: update `PRIVACY.md`, the in-app policy, the privacy manifest and the App Privacy label together.
- Ask for a permission only at the moment it's needed, with a purpose string that says why in plain words.
- Prefer system pickers (`PhotosPicker`, `PasteButton`, Shortcuts parameters) over broad permissions.
- Keep user data on device by default; make saving opt-in and erasable.
- Never put personal data in URLs, logs or analytics.
- Label anything that isn't a real result (demos, samples) wherever it appears.
