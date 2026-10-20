import { browser, type Browser } from "wxt/browser";
import { defineBackground } from "wxt/utils/define-background";

import { putPending, type PendingCheck } from "../lib/pending";

/*
 * Like the phone share sheet: right-click a photo or post on Bluesky, and the
 * side panel opens with its result.
 */

const POST_PATTERN = "https://bsky.app/profile/*/post/*";

/** Firefox shows the panel as a sidebar, opened through `sidebarAction`. */
const sidebarAction = (browser as unknown as { sidebarAction?: { open(): Promise<void>; toggle(): Promise<void> } }).sidebarAction;

export default defineBackground(() => {
  browser.runtime.onInstalled.addListener(async () => {
    await browser.contextMenus.removeAll();
    browser.contextMenus.create({
      id: "check-image",
      title: "Check photo with WildcatVerify",
      contexts: ["image"],
      targetUrlPatterns: ["https://cdn.bsky.app/*"],
    });
    browser.contextMenus.create({
      id: "check-link",
      title: "Check post with WildcatVerify",
      contexts: ["link"],
      targetUrlPatterns: [POST_PATTERN],
    });
    browser.contextMenus.create({
      id: "check-page",
      title: "Check this post with WildcatVerify",
      contexts: ["page"],
      documentUrlPatterns: [POST_PATTERN],
    });
  });

  // Chrome: the toolbar button opens the side panel. Firefox: it toggles the sidebar.
  browser.sidePanel?.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  if (sidebarAction) browser.action.onClicked.addListener(() => void sidebarAction.toggle());

  browser.contextMenus.onClicked.addListener((info, tab) => {
    const check = pendingFor(info);
    if (!check) return;
    // Opening the panel must happen inside the click, before anything is awaited.
    openPanel(tab);
    void putPending(check);
  });
});

function pendingFor(info: Browser.contextMenus.OnClickData): PendingCheck | null {
  const at = Date.now();
  if (info.menuItemId === "check-image" && info.srcUrl) return { kind: "image", imageUrl: info.srcUrl, at };
  if (info.menuItemId === "check-link" && info.linkUrl) return { kind: "post", link: info.linkUrl, at };
  if (info.menuItemId === "check-page" && info.pageUrl) return { kind: "post", link: info.pageUrl, at };
  return null;
}

function openPanel(tab: Browser.tabs.Tab | undefined) {
  if (sidebarAction) {
    void sidebarAction.open();
    return;
  }
  if (tab?.windowId !== undefined) void browser.sidePanel.open({ windowId: tab.windowId }).catch(() => {});
}
