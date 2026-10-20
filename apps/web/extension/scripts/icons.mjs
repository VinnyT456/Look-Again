// Renders the extension's toolbar icons from the specimen glyph (see src/components/brand.tsx):
// a framed patch grid with one lit cell, on the UV-violet ground.
// Run with `npm run ext:icons`; the PNGs are committed under extension/public/icon.
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const out = resolve(dirname(fileURLToPath(import.meta.url)), "../public/icon");

// The 22-unit glyph centred on a 32-unit rounded square. Small sizes drop the
// faint cells, which would blur into the frame.
const svg = (detailed) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="7" fill="#2e1d4d"/>
  <g transform="translate(5 5)">
    <rect x="0.75" y="0.75" width="20.5" height="20.5" rx="2.5" fill="none" stroke="#ede8f7" stroke-width="${detailed ? 1.5 : 2}"/>
    ${
      detailed
        ? `<g fill="#ede8f7" opacity="0.4">
      <rect x="4.5" y="4.5" width="3.5" height="3.5"/><rect x="9.25" y="4.5" width="3.5" height="3.5"/><rect x="14" y="4.5" width="3.5" height="3.5"/>
      <rect x="4.5" y="9.25" width="3.5" height="3.5"/><rect x="9.25" y="9.25" width="3.5" height="3.5"/>
      <rect x="4.5" y="14" width="3.5" height="3.5"/><rect x="9.25" y="14" width="3.5" height="3.5"/><rect x="14" y="14" width="3.5" height="3.5"/>
    </g>
    <rect x="14" y="9.25" width="3.5" height="3.5" fill="#b6ee52"/>`
        : `<rect x="12.5" y="7.75" width="6" height="6" fill="#b6ee52"/>`
    }
  </g>
</svg>`;

await mkdir(out, { recursive: true });
for (const size of [16, 32, 48, 128]) {
  await sharp(Buffer.from(svg(size >= 32)), { density: 72 * (size / 32) * 4 })
    .resize(size, size)
    .png()
    .toFile(resolve(out, `${size}.png`));
}
console.log(`Wrote icons to ${out}`);
