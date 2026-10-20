import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

/*
 * The WildcatVerify browser extension. It lives beside the Next.js app and
 * reuses its components and models (`@/…` resolves into `../src`), so the
 * side panel shows the same Results and Analyzing views as the web.
 */

export default defineConfig({
  srcDir: ".",
  modules: ["@wxt-dev/module-react"],
  hooks: {
    // WXT points `@` at its own srcDir after reading this config; the web app's `@/…` imports need `../src`.
    "config:resolved": (wxt) => {
      wxt.config.alias["@"] = resolve(__dirname, "../src");
    },
  },
  alias: {
    // ui.tsx links with next/link; outside Next a plain anchor does the same job.
    "next/link": resolve(__dirname, "shims/next-link.tsx"),
  },
  vite: () => ({
    plugins: [tailwindcss()],
    build: {
      rollupOptions: {
        // Shared components carry Next's "use client" directive, which means nothing here.
        onwarn(warning, warn) {
          if (warning.code === "MODULE_LEVEL_DIRECTIVE") return;
          warn(warning);
        },
      },
    },
  }),
  manifest: ({ browser }) => ({
    name: "WildcatVerify",
    version: "0.1.0",
    description: "Check whether a photo on Bluesky is likely real or AI-generated, right where you found it.",
    permissions: ["contextMenus", "storage", ...(browser === "firefox" ? [] : ["sidePanel"])],
    // Bluesky, to read which post is open; localhost, the default WildcatVerify server.
    host_permissions: ["https://bsky.app/*", "http://localhost/*", "http://127.0.0.1/*"],
    // Asked for in Options only when someone points the extension at another server.
    optional_host_permissions: ["https://*/*", "http://*/*"],
    action: { default_title: "Open WildcatVerify" },
    icons: { 16: "icon/16.png", 32: "icon/32.png", 48: "icon/48.png", 128: "icon/128.png" },
    ...(browser === "firefox" && {
      browser_specific_settings: {
        gecko: {
          id: "wildcatverify@look-again",
          strict_min_version: "121.0",
          // Photos from the page go to the configured WildcatVerify server to be checked.
          data_collection_permissions: { required: ["websiteContent"] },
        },
      },
    }),
  }),
});
