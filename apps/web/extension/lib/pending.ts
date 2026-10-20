import { browser } from "wxt/browser";

/**
 * A check asked for from a page (the right-click menu), handed from the
 * background to the side panel through session storage. Session storage is
 * cleared when the browser closes, and the panel removes the request as soon
 * as it starts the check.
 */
export type PendingCheck = { kind: "image"; imageUrl: string; at: number } | { kind: "post"; link: string; at: number };

const KEY = "pending";

export const putPending = (check: PendingCheck) => browser.storage.session.set({ [KEY]: check });

/** Takes the waiting request, if any, so it runs once. */
export async function takePending(): Promise<PendingCheck | null> {
  const check = (await browser.storage.session.get(KEY))[KEY] as PendingCheck | undefined;
  if (!check) return null;
  await browser.storage.session.remove(KEY);
  return check;
}

/** Calls back whenever a new request arrives while the panel is open. */
export function onPending(listener: () => void) {
  const handle = (changes: Record<string, { newValue?: unknown }>, area: string) => {
    if (area === "session" && changes[KEY]?.newValue) listener();
  };
  browser.storage.onChanged.addListener(handle);
  return () => browser.storage.onChanged.removeListener(handle);
}
