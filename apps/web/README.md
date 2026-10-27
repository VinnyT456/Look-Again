# WildcatVerify web and browser extension

The web version of WildcatVerify: check whether a photo on Bluesky is likely
real or AI-generated, see where the detector looked, and practise spotting
fakes. A browser extension in [`extension/`](extension/) checks photos and
posts right where you find them, using the same components.

Product and design records live at the repo root: [`PRODUCT.md`](../../PRODUCT.md)
and [`DESIGN.md`](../../DESIGN.md).

## Layout

```text
apps/web/
├── src/app/            # Next.js routes: Check (/), Feed, My Checks, Learn, Settings, API
├── src/components/     # Screens and the shared condition-report UI (also used by the extension)
├── src/lib/            # Models, Bluesky client, check pipeline, client store
└── extension/          # WXT browser extension (side panel, options, background)
```

## Run the web app

```bash
npm install
npm run dev
```

Open http://localhost:3000. Checks go to the detector service in `ml/`
(`DETECTOR_URL`, default `http://127.0.0.1:8765`):

```bash
cd ../../ml
uv sync --extra serve
uv run uvicorn look_again.serve.app:app --host 127.0.0.1 --port 8765
```

When the detector isn't running, results come from a demo classifier and are
always labelled **Demo result**.

## Browser extension

The extension mirrors the phone share sheet:

- **Right-click a photo on Bluesky** → *Check photo with WildcatVerify*, or
  right-click a post link → *Check post with WildcatVerify*. The side panel
  opens with the result.
- **Toolbar button** opens the panel, which offers *Check this post* for the
  Bluesky post on the current tab, a link field, and drop/paste/choose a photo.
- **Done** discards the result. **Open in My Checks** hands it to the web app
  (`/checks#import=…`), which keeps it only if Keep My Checks is on there.
- **Options** set the WildcatVerify server (default `http://localhost:3000`).
  Any other server asks for permission to reach it first.

The extension talks to the web app's API, so keep `npm run dev` (or a deployed
web app) running.

```bash
npm run ext:dev            # Chrome with hot reload
npm run ext:build          # extension/.output/chrome-mv3
npm run ext:build:firefox  # extension/.output/firefox-mv3
npm run ext:zip            # store-ready zip
npm run ext:typecheck
```

To load a build by hand in Chrome: `chrome://extensions` → Developer mode →
**Load unpacked** → `extension/.output/chrome-mv3`. In Firefox:
`about:debugging` → This Firefox → **Load Temporary Add-on** → the
`manifest.json` in `extension/.output/firefox-mv3`.

Permissions: `contextMenus`, `storage`, `sidePanel` (Chrome), plus host access
to `bsky.app` (to see which post is open) and localhost (the default server).

Shared code: the extension imports `@/…` from `src/` (see
`extension/wxt.config.ts`); `next/link` is swapped for a plain anchor there.
Toolbar icons are rendered from the specimen glyph with `npm run ext:icons`.

## Checks

```bash
npm run lint
npx tsc --noEmit
npm run build
```

See [PRIVACY.md](PRIVACY.md) for what is sent where.
