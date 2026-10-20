import { browser } from "wxt/browser";

/*
 * The extension's own preferences, in extension storage on this device.
 * Results themselves are never stored here: Done discards them.
 */

export const DEFAULT_SERVER = "http://localhost:3000";

export interface ExtensionSettings {
  /** The WildcatVerify web app the extension checks photos with. */
  server: string;
  /** Show the detector's heatmap under Detector light on Likely AI results. */
  showHeatmap: boolean;
}

export const defaultExtensionSettings: ExtensionSettings = { server: DEFAULT_SERVER, showHeatmap: true };

const KEY = "settings";

export async function loadExtensionSettings(): Promise<ExtensionSettings> {
  const stored = (await browser.storage.local.get(KEY))[KEY] as Partial<ExtensionSettings> | undefined;
  return { ...defaultExtensionSettings, ...stored };
}

export const saveExtensionSettings = (settings: ExtensionSettings) => browser.storage.local.set({ [KEY]: settings });

export function onExtensionSettingsChange(listener: (settings: ExtensionSettings) => void) {
  const handle = (changes: Record<string, { newValue?: unknown }>, area: string) => {
    if (area === "local" && KEY in changes) listener({ ...defaultExtensionSettings, ...(changes[KEY].newValue as Partial<ExtensionSettings>) });
  };
  browser.storage.onChanged.addListener(handle);
  return () => browser.storage.onChanged.removeListener(handle);
}

/** "https://verify.example.edu/" → "https://verify.example.edu"; null when it isn't an http(s) address. */
export function normalizeServer(value: string): string | null {
  let text = value.trim();
  if (!text) return null;
  if (!/^https?:\/\//i.test(text)) text = `${/^(localhost|127\.0\.0\.1)(:|$)/.test(text) ? "http" : "https"}://${text}`;
  try {
    const url = new URL(text);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.origin;
  } catch {
    return null;
  }
}

/** The host permission pattern for a server origin, e.g. `https://verify.example.edu/*`. */
export const originPattern = (server: string) => `${new URL(server).protocol}//${new URL(server).hostname}/*`;
