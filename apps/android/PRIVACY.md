# WildcatVerify Privacy Policy (Android)

Last updated October 19, 2026.

WildcatVerify is built so your photos and checks stay on your device.

## Photos you choose

Android's photo picker gives the app only the photo you pick, never the rest of your library. It is analyzed in memory on your device, never uploaded or written to disk, and is discarded when you delete the check, clear My Checks, or the app is closed. Location and other personal metadata aren't read. If the photo carries Content Credentials, only the app or device that made it and its edit history are read and shown with the result.

## Items you share

When you use Share → WildcatVerify in another app, only what you shared reaches the app. It is checked in memory the same way and discarded when you tap Done.

## Labels

- **The label tab** is off unless you start it. Each time, Android asks you to approve screen sharing; on Android 14 and later you can share only the Bluesky app. Screen frames are kept in memory, replaced as you scroll, and never uploaded or saved. Android shows a sharing indicator and WildcatVerify shows a notification while it runs.
- **Auto-Label** (sideload builds only) is off unless you turn it on in Android's Accessibility settings. It looks only at the Bluesky app and at Chrome while bsky.app is open, reads where photos are on screen, and takes a screenshot to read those photos' pixels, all in memory on your device.

## Your Bluesky account

Signing in is optional and only used to show your Following feed. Use an app password; WildcatVerify sends it to Bluesky once and keeps only the sign-in token, encrypted with a key stored in Android's Keystore. Signing out or Erase All Data deletes it.

## The Feed and copied links

With Check Posts Automatically on (Settings → Feed), each Feed post's image is analyzed on your device as it appears; those verdicts stay in memory and aren't added to My Checks unless you open the post. Automatic checks pause in Battery Saver and on mobile data or Data Saver.

When you open the app, it asks Android only whether the clipboard looks like a link, from its description, without reading it. The link is read only when you tap Paste.

## Bluesky links and the Feed

To check a post or load the Feed, the app asks Bluesky directly. Bluesky sees your IP address like any website would. WildcatVerify runs no server and keeps no copy of the link. See Bluesky's privacy policy: https://bsky.social/about/support/privacy-policy

## My Checks

By default, past checks are kept in memory and disappear when the app is closed. If you turn on Settings → Keep My Checks, results and small copies of the photos you checked are saved on your device only: in the app's private storage, left out of backups, never uploaded, and deleted when you turn the setting off or erase your data.

## Hidden accounts and settings

Accounts you hide from the Feed, your preferences and your best Look Again score are saved on your device only. Bluesky and hidden accounts aren't told. Erase All Data removes them.

## Where processing happens

All image analysis, including the AI-image detector, runs on your device with LiteRT. Nothing is sent to the developer or to any AI service.

## Your choices

Delete one check with a swipe, clear My Checks, or use Settings → Erase All Data. Uninstalling the app removes everything. The developer holds no personal data, but you can still contact us with any privacy request.

## What the app doesn't do

- No account needed; Bluesky sign-in is optional
- No analytics, ads or tracking
- No data sold, shared or collected

Contact: https://github.com/VinnyT456/Look-Again/issues
