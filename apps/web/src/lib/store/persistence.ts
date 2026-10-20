import type { VerificationCase } from "../models/verification-case";

/*
 * Keep My Checks saves results (and small copies of uploaded photos) in this
 * browser's IndexedDB. Nothing here is sent anywhere.
 */

const DB = "wildcatverify";
const CHECKS = "checks";

export interface SavedCheck {
  item: VerificationCase;
  photo?: Blob;
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(CHECKS);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Saved checks, newest first. Missing or unreadable data gives an empty list. */
export async function loadChecks(): Promise<SavedCheck[]> {
  try {
    const db = await open();
    const rows = await new Promise<SavedCheck[]>((resolve, reject) => {
      const request = db.transaction(CHECKS).objectStore(CHECKS).get("all");
      request.onsuccess = () => resolve((request.result as SavedCheck[] | undefined) ?? []);
      request.onerror = () => reject(request.error);
    });
    db.close();
    return rows;
  } catch {
    return [];
  }
}

export async function saveChecks(rows: SavedCheck[]) {
  const db = await open();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(CHECKS, "readwrite");
    tx.objectStore(CHECKS).put(rows, "all");
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export function eraseChecks() {
  return new Promise<void>((resolve) => {
    const request = indexedDB.deleteDatabase(DB);
    request.onsuccess = request.onerror = request.onblocked = () => resolve();
  });
}

const SETTINGS_KEY = "wildcatverify.settings";
const BEST_KEY = "wildcatverify.bestScore";

export interface Settings {
  /** Save My Checks in this browser between visits. Off by default. */
  keepHistory: boolean;
  /** Show the detector's heatmap under Highlight on Likely AI results. */
  showHeatmap: boolean;
}

export const defaultSettings: Settings = { keepHistory: false, showHeatmap: true };

export function loadSettings(): Settings {
  try {
    return { ...defaultSettings, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? "{}") };
  } catch {
    return defaultSettings;
  }
}

export const saveSettings = (settings: Settings) => localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));

export function loadBestScore(): number | null {
  const value = Number(localStorage.getItem(BEST_KEY));
  return localStorage.getItem(BEST_KEY) !== null && Number.isFinite(value) ? value : null;
}

export const saveBestScore = (score: number) => localStorage.setItem(BEST_KEY, String(score));

export function eraseLocalStorage() {
  localStorage.removeItem(SETTINGS_KEY);
  localStorage.removeItem(BEST_KEY);
}
