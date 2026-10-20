# WildcatVerify Privacy Policy

_Last updated: October 15, 2026_

WildcatVerify helps you judge whether a photo is genuine, edited, or AI-generated.
It is built so that your photos and checks stay on your iPhone.

## What the app does with your data

**Photos you choose.** When you pick a photo or screenshot, iOS gives WildcatVerify
only that one image; the app cannot see the rest of your library. The image is
decoded and analyzed in memory on your iPhone. It is never uploaded, never written
to disk, and is discarded when you delete the check, clear My Checks, or quit the
app. Location and other personal metadata embedded in the photo are not read: the app
re-renders the pixels only. The one exception is **Content Credentials** (C2PA), a
provenance record some cameras and AI tools attach: the app reads which app or device made
the photo and its edit history, and shows them with the result. Names, locations and other
identity details in those credentials are ignored.

**Items you share to WildcatVerify.** When you use Share → WildcatVerify (or
Share → Check with WildcatVerify) in
another app, only the photo, link or text you shared is passed to the app. It is
checked in memory the same way, and discarded when you tap Done. Nothing from the
share sheet is saved or uploaded.

**Siri and Shortcuts.** The **Check Image** action receives the image your shortcut
passes it (for example, from Take Screenshot) directly, in memory. WildcatVerify
never reads your photo library and needs no Photos permission for this. You box the
photo, only that area is checked on your iPhone, and the screenshot itself is
discarded. **Visual Intelligence** (on iPhones with Apple
Intelligence) passes the screenshot or camera image you search with to WildcatVerify in
memory; it is held only until you tap the result, then checked like any other screenshot.
**Check the copied link** reads the clipboard only when you run it, and iOS
asks your permission first. Only a Bluesky post link is used; anything else on the
clipboard is ignored and never stored.

**Bluesky links you paste or share.** To check a Bluesky post, the app sends the post's
address to Bluesky's public API (`public.api.bsky.app`) and downloads that post's
text and photo. This request goes directly from your iPhone to Bluesky, the same as
opening the post in a browser. Bluesky receives your device's IP address as part of
any internet request and handles it under its own privacy policy:
https://bsky.social/about/support/privacy-policy. WildcatVerify does not
operate a server and does not receive or keep the link.

**My Checks.** By default your past checks are kept in memory for the current
session only and disappear when you close the app. If you turn on **Settings →
Keep My Checks**, your results and small copies (up to 1024 px) of photos you
checked are saved in the app's private storage on this iPhone. They are encrypted
while the phone is locked, left out of iCloud and computer backups, never uploaded,
and deleted when you turn the setting off, clear My Checks, or choose **Erase All
Data**. You can delete one check with a swipe.

**The Feed.** The Feed tab loads public image posts from Bluesky's "What's Hot"
feed directly from Bluesky (`public.api.bsky.app`), like opening it in a browser.
No account is used and nothing about you is sent beyond the request itself. With
**Check Posts Automatically** on (the default), each post's image is analyzed on
your iPhone as it scrolls into view; the verdict is kept in memory only and isn't
added to My Checks unless you open the post. You can turn this off under
**Settings → Feed**.

**Copied links.** When you open WildcatVerify, it asks iOS only *whether* the
clipboard holds something that looks like a link, which doesn't reveal the link
and doesn't trigger a paste prompt. The link itself is read only when you tap
**Paste**.

**Hidden accounts.** When you hide an account from the Feed, its Bluesky ID and handle
are saved on this iPhone so it stays hidden. Bluesky and the account are not told. You can
show it again under **Settings → Hidden Accounts**, and **Erase All Data** removes the list.

**Settings.** Your preferences (Keep My Checks, haptics, heatmap, whether you closed the Siri tip,
your best Look Again score, hidden accounts) are stored on this
iPhone in the app's settings and are never sent anywhere.

## Where processing happens

All image analysis, including the AI-image detector, runs on your iPhone with Apple's Core ML.
No photo, screenshot, link or result is sent to the developer or to any AI service.

**Apple services.** If you use Siri or Shortcuts, Apple processes your voice request under
Apple's own privacy policy. WildcatVerify only receives the image or link the shortcut passes.

## What is kept, and for how long

| Data | Where | How long |
|---|---|---|
| Photos and screenshots you check | Memory on your iPhone | Until you delete the check or quit the app |
| My Checks (if **Keep My Checks** is on) | App storage on your iPhone, not backed up | Until you turn it off, delete it, or erase data |
| Settings, best score, hidden accounts | App settings on your iPhone | Until you change them or erase data |
| Clipboard contents | Read only when you run Check Copied Link | Not kept; only a Bluesky link is used |
| Anything on a server | Nowhere | WildcatVerify has no server |

## Your choices and rights

Everything WildcatVerify keeps is on your iPhone and under your control: delete one check
with a swipe, clear My Checks, or use **Settings → Erase All Data**. Deleting the app removes
everything. Because the developer receives no personal data, there is nothing held elsewhere
to access, correct, export or delete; requests under laws such as the GDPR or CCPA can still be
sent to the contact below and will be answered.

## What the app does not do

- No account, sign-in, or personal information is requested.
- Nothing is uploaded: all checks run on your iPhone.
- No analytics, advertising, or crash-reporting SDKs are included.
- No tracking across apps or websites, and no data is sold or shared.
- No data is collected by the developer. In App Store terms: **Data Not Collected**.

## Children

WildcatVerify does not knowingly collect information from anyone, including
children under 13.

## Changes

If a future version changes how data is handled (for example, a hosted detection
model or a live feed), this policy will be updated before that version ships, and
the in-app copy under **About → Privacy Policy** will match it.

## Contact

Questions about this policy: open an issue at
https://github.com/VinnyT456/Look-Again/issues.
