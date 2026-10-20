import type { Metadata } from "next";

import { DocLink, DocPage, DocSection } from "@/components/doc";
import { appLinks } from "@/lib/links";

export const metadata: Metadata = { title: "Credits" };

export default function CreditsPage() {
  return (
    <DocPage title="Credits" intro="The detector behind WildcatVerify, and where it comes from.">
      <DocSection title="CommunityForensics ViT">
        <p>
          The detector is built on the Community Forensics model by Jeongsoo Park and Andrew Owens, trained on images from 4,803 generators. Hugging Face conversion by
          Han Yoon, Borderless / Ethix R&amp;D.
        </p>
        <p>WildcatVerify adds a linear probe and the patch heatmap on top, and runs the detector on its own server.</p>
      </DocSection>
      <DocSection title="Detection model">
        <p>
          Park, J. and Owens, A. &ldquo;Community Forensics: Using Thousands of Generators to Train Fake Image Detectors.&rdquo; CVPR 2025, pp. 8245–8257.
        </p>
        <p className="flex flex-wrap gap-x-5 gap-y-2">
          <DocLink href={appLinks.detectorPaper}>Read the paper</DocLink>
          <DocLink href={appLinks.detectorCode}>Original code</DocLink>
          <DocLink href={appLinks.detectorModel}>Model on Hugging Face</DocLink>
        </p>
      </DocSection>
      <DocSection title="License">
        <p>The Community Forensics model and code are released under the MIT License.</p>
      </DocSection>
    </DocPage>
  );
}
