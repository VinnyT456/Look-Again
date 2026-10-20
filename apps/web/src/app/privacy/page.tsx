import type { Metadata } from "next";

import { DocLink, DocPage, DocSection } from "@/components/doc";
import { appLinks } from "@/lib/links";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <DocPage title="Privacy Policy" intro="WildcatVerify is built so your photos and checks stay private. Last updated October 15, 2026.">
      <DocSection title="Photos you choose">
        <p>
          Your browser gives the site only the photo you choose, drop or paste. It is sent to the WildcatVerify server to be checked, held in memory there only while
          it is analyzed, and never written to disk or kept. In this browser it stays in memory and is discarded when you delete the check, clear My Checks, or close the
          tab.
        </p>
      </DocSection>
      <DocSection title="Bluesky links you paste">
        <p>
          To check a post, the WildcatVerify server asks Bluesky&apos;s public API for that post&apos;s text and photo. No account is used, and the server keeps no copy
          of the link.
        </p>
        <p>
          <DocLink href={appLinks.blueskyPrivacy}>Bluesky Privacy Policy</DocLink>
        </p>
      </DocSection>
      <DocSection title="The Feed">
        <p>
          The Feed loads public image posts from Bluesky&apos;s What&apos;s Hot feed. Images and avatars load straight from Bluesky&apos;s servers, which see your IP
          address like any website would. Posts are only checked when you choose them.
        </p>
      </DocSection>
      <DocSection title="The browser extension">
        <p>
          When you check an image or post from the extension, only that image or link is sent to the WildcatVerify server, checked the same way, and discarded when you
          choose Done.
        </p>
      </DocSection>
      <DocSection title="My Checks">
        <p>
          By default, past checks are kept in memory and disappear when you close the tab. If you turn on Settings → Keep My Checks, results and small copies of the
          photos you checked are saved in this browser only, never uploaded, and deleted when you turn the setting off or erase your data.
        </p>
      </DocSection>
      <DocSection title="Settings and score">
        <p>Your preferences and your best Look Again score are saved in this browser only. Erase All Data removes them.</p>
      </DocSection>
      <DocSection title="What the site doesn't do">
        <ul className="flex flex-col gap-1">
          <li>No account or sign-in</li>
          <li>No analytics, ads or tracking</li>
          <li>No data sold, shared or collected</li>
        </ul>
      </DocSection>
      <DocSection title="Your choices">
        <p>
          Delete one check, clear My Checks, or use Settings → Erase All Data. Clearing this site&apos;s data in your browser removes everything. The developer holds no
          personal data, but you can still contact us with any privacy request.
        </p>
        <p>
          <DocLink href={appLinks.support}>Contact Support</DocLink>
        </p>
      </DocSection>
    </DocPage>
  );
}
