import { apiClient, ApiError } from "../api/client";
import { practiceBank } from "../learn/practice-bank";
import { drawRound, type PracticeAnswer, type PracticeQuestion } from "../learn/practice";
import { checkErrorMessages, genericCheckError } from "../models/errors";
import type { FeedPost } from "../models/feed";
import { verdictLabel, type VerdictFilter } from "../models/verdict";
import type { VerificationCase } from "../models/verification-case";
import { dropAllUploads, dropUpload, imageSrc, keepUpload, smallCopy, uploadBlob } from "./images";
import {
  defaultSettings,
  eraseChecks,
  eraseLocalStorage,
  loadBestScore,
  loadChecks,
  loadSettings,
  saveBestScore,
  saveChecks,
  saveSettings,
  type SavedCheck,
  type Settings,
} from "./persistence";
import { createStore } from "./store";

export const api = apiClient();

export type PracticePhase = { kind: "answering" } | { kind: "revealed"; picked: PracticeAnswer } | { kind: "finished" };

/** A one-off check (a Feed post): analyzing, then the result or what went wrong. */
export type OneOffCheck = { kind: "analyzing" } | { kind: "result"; item: VerificationCase } | { kind: "failed"; message: string };

interface AppState {
  /** Settings and saved checks have been read from this browser. */
  hydrated: boolean;
  settings: Settings;
  cases: VerificationCase[];
  /** Checks added since My Checks was last opened; drives the tab badge. */
  unseen: number;
  /** Text for screen readers when a verdict arrives. */
  announcement: string;
  /** Whether the trained detector answered; null until asked. When false, results come from the demo classifier. */
  detectorReady: boolean | null;

  checkInput: string;
  checkAnalyzing: boolean;
  checkPreview: string | null;
  checkError: string | null;
  /** Results pushed on the Check tab. */
  checkPath: VerificationCase[];

  historyPath: VerificationCase[];
  historyQuery: string;
  historyFilter: VerdictFilter;

  feedPosts: FeedPost[];
  feedCursor: string | null;
  feedStatus: "idle" | "loading" | "loaded" | "failed";
  feedError: string | null;
  feedLoadingMore: boolean;
  feedOpen: FeedPost | null;
  feedCheck: OneOffCheck | null;

  practiceRound: PracticeQuestion[];
  practiceIndex: number;
  practicePicks: PracticeAnswer[];
  practicePhase: PracticePhase;
  /** Bumped on each answer, so feedback plays once per pick. */
  practiceAnswerCount: number;
  bestScore: number | null;
  lastRoundWasNewBest: boolean;
}

export const app = createStore<AppState>({
  hydrated: false,
  settings: defaultSettings,
  cases: [],
  unseen: 0,
  announcement: "",
  detectorReady: null,
  checkInput: "",
  checkAnalyzing: false,
  checkPreview: null,
  checkError: null,
  checkPath: [],
  historyPath: [],
  historyQuery: "",
  historyFilter: "all",
  feedPosts: [],
  feedCursor: null,
  feedStatus: "idle",
  feedError: null,
  feedLoadingMore: false,
  feedOpen: null,
  feedCheck: null,
  // The server render and first client render share this fixed round; a shuffled one replaces it on hydrate.
  practiceRound: practiceBank.slice(0, 8),
  practiceIndex: 0,
  practicePicks: [],
  practicePhase: { kind: "answering" },
  practiceAnswerCount: 0,
  bestScore: null,
  lastRoundWasNewBest: false,
});

const messageOf = (error: unknown) => (error instanceof ApiError ? error.message : genericCheckError);

// MARK: Startup

/** Reads settings and, when Keep My Checks is on, saved checks. Runs once on the client. */
export async function hydrate() {
  if (app.get().hydrated) return;
  api
    .detectorReady()
    .then((ready) => app.set({ detectorReady: ready }))
    .catch(() => app.set({ detectorReady: false }));
  const settings = loadSettings();
  let cases: VerificationCase[] = [];
  if (settings.keepHistory) {
    cases = (await loadChecks()).map(({ item, photo }) => {
      if (photo) keepUpload(item.id, photo);
      return item;
    });
  }
  app.set({ hydrated: true, settings, cases, bestScore: loadBestScore() });
  restartPractice();
  importFromHash();
}

/** The browser extension hands a result over as `#import=<base64 JSON>`, so it can be kept in My Checks. */
function importFromHash() {
  const match = location.hash.match(/^#import=(.+)$/);
  if (!match) return;
  history.replaceState(null, "", location.pathname);
  try {
    const item = JSON.parse(decodeURIComponent(escape(atob(match[1])))) as VerificationCase;
    if (typeof item.id === "string" && typeof item.verdict === "string") {
      record(item);
      app.set({ historyPath: [item] });
    }
  } catch {
    // A malformed hand-off is ignored.
  }
}

// MARK: My Checks

const savedPhotos = new Map<string, Blob>();

async function persist() {
  const { settings, cases } = app.get();
  if (!settings.keepHistory) return;
  try {
    const rows: SavedCheck[] = await Promise.all(
      cases.map(async (item) => {
        const blob = item.imageUrl ? uploadBlob(item.imageUrl) : null;
        if (!blob) return { item };
        let photo = savedPhotos.get(item.id);
        if (!photo) {
          photo = await smallCopy(blob);
          savedPhotos.set(item.id, photo);
        }
        return { item, photo };
      }),
    );
    await saveChecks(rows);
  } catch (error) {
    console.warn("Couldn't save My Checks", error);
  }
}

/** Adds a case to the top of My Checks, or moves it there if already present. */
export function record(item: VerificationCase) {
  app.set((s) => ({
    cases: [item, ...s.cases.filter((c) => c.id !== item.id)],
    unseen: s.unseen + 1,
    announcement: `${verdictLabel[item.verdict]}, ${item.confidencePercentage} percent confidence`,
  }));
  void persist();
}

export const markSeen = () => app.get().unseen > 0 && app.set({ unseen: 0 });

export function removeCase(item: VerificationCase) {
  app.set((s) => ({ cases: s.cases.filter((c) => c.id !== item.id) }));
  dropUpload(item.imageUrl);
  savedPhotos.delete(item.id);
  void persist();
}

export function clearCases() {
  app.set({ cases: [], unseen: 0, historyPath: [], historyQuery: "", historyFilter: "all", checkPath: [] });
  dropAllUploads();
  savedPhotos.clear();
  void persist();
}

// MARK: Settings

export function updateSettings(change: Partial<Settings>) {
  const settings = { ...app.get().settings, ...change };
  app.set({ settings });
  saveSettings(settings);
  if (change.keepHistory === true) void persist();
  if (change.keepHistory === false) {
    savedPhotos.clear();
    void eraseChecks();
  }
}

/** Settings → Erase All Data: checks, saved photos, best score and preferences. */
export async function eraseAllData() {
  clearCases();
  await eraseChecks();
  eraseLocalStorage();
  app.set({ settings: defaultSettings, bestScore: null, lastRoundWasNewBest: false });
}

// MARK: Check tab

let checkController: AbortController | null = null;

async function runCheck(preview: string | null, work: (signal: AbortSignal) => Promise<VerificationCase>) {
  checkController?.abort();
  const controller = new AbortController();
  checkController = controller;
  app.set({ checkAnalyzing: true, checkPreview: preview, checkError: null });
  try {
    const item = await work(controller.signal);
    if (controller.signal.aborted) return;
    record(item);
    app.set((s) => ({ checkAnalyzing: false, checkPreview: null, checkInput: "", checkPath: [...s.checkPath, item] }));
    return item;
  } catch (error) {
    // Superseded by the user (Cancel, a new check, or Check Another); whatever they did owns the state now.
    if (controller.signal.aborted) return;
    app.set({ checkAnalyzing: false, checkPreview: null, checkError: messageOf(error) });
    throw error;
  } finally {
    if (checkController === controller) checkController = null;
  }
}

export function checkLink() {
  const link = app.get().checkInput.trim();
  if (!link || app.get().checkAnalyzing) return;
  void runCheck(null, (signal) => api.checkLink(link, signal)).catch(() => {});
}

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

export function checkPhoto(file: File) {
  if (!file.type.startsWith("image/")) {
    app.set({ checkError: checkErrorMessages.unsupported });
    return;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    app.set({ checkError: checkErrorMessages.tooLarge });
    return;
  }
  const id = crypto.randomUUID();
  const url = keepUpload(id, file);
  void runCheck(imageSrc(url), async (signal) => ({ ...(await api.checkFile(file, signal)), id, imageUrl: url }))
    .then((item) => !item && dropUpload(url))
    .catch(() => dropUpload(url));
}

export function cancelCheck() {
  checkController?.abort();
  checkController = null;
  app.set({ checkAnalyzing: false, checkPreview: null });
}

/** "Check Another Image" from any results screen: unwinds every stack and lands on a fresh Check form. */
export function startNewCheck() {
  cancelCheck();
  closeFeedPost();
  app.set({ checkInput: "", checkError: null, checkPath: [], historyPath: [] });
}

// MARK: Feed

let feedRequest = 0;

export async function loadFeed(refresh = false) {
  const { feedStatus } = app.get();
  if (!refresh && (feedStatus === "loading" || feedStatus === "loaded")) return;
  const request = ++feedRequest;
  app.set({ feedStatus: "loading", feedError: null });
  try {
    const page = await api.feedPage(null);
    if (request !== feedRequest) return;
    app.set({ feedPosts: page.posts, feedCursor: page.cursor, feedStatus: "loaded" });
  } catch (error) {
    if (request !== feedRequest) return;
    app.set({ feedStatus: "failed", feedError: messageOf(error) });
  }
}

export async function loadMoreFeed() {
  const { feedCursor, feedLoadingMore, feedStatus } = app.get();
  if (!feedCursor || feedLoadingMore || feedStatus !== "loaded") return;
  const request = feedRequest;
  app.set({ feedLoadingMore: true });
  try {
    const page = await api.feedPage(feedCursor);
    if (request !== feedRequest) return;
    app.set((s) => {
      const seen = new Set(s.feedPosts.map((p) => p.id));
      return { feedPosts: [...s.feedPosts, ...page.posts.filter((p) => !seen.has(p.id))], feedCursor: page.cursor };
    });
  } catch {
    // The next scroll to the end tries again.
  } finally {
    if (request === feedRequest) app.set({ feedLoadingMore: false });
  }
}

let feedController: AbortController | null = null;

/** Checks a Feed post's first photo; the result goes to My Checks. */
export async function openFeedPost(post: FeedPost) {
  feedController?.abort();
  const controller = new AbortController();
  feedController = controller;
  app.set({ feedOpen: post, feedCheck: { kind: "analyzing" } });
  try {
    const item = await api.checkFeedPost(post, controller.signal);
    if (controller.signal.aborted) return;
    record(item);
    app.set({ feedCheck: { kind: "result", item } });
  } catch (error) {
    if (controller.signal.aborted) return;
    app.set({ feedCheck: { kind: "failed", message: messageOf(error) } });
  }
}

export function closeFeedPost() {
  feedController?.abort();
  feedController = null;
  app.set({ feedOpen: null, feedCheck: null });
}

// MARK: Learn

let lastRoundIds = new Set<string>();

export function restartPractice() {
  const round = drawRound(practiceBank, lastRoundIds);
  lastRoundIds = new Set(round.map((q) => q.id));
  app.set({ practiceRound: round, practiceIndex: 0, practicePicks: [], practicePhase: { kind: "answering" } });
}

export function selectAnswer(answer: PracticeAnswer) {
  const s = app.get();
  if (s.practicePhase.kind !== "answering" || !s.practiceRound[s.practiceIndex]) return;
  app.set({
    practicePicks: [...s.practicePicks, answer],
    practicePhase: { kind: "revealed", picked: answer },
    practiceAnswerCount: s.practiceAnswerCount + 1,
  });
}

export function nextQuestion() {
  const s = app.get();
  if (s.practicePhase.kind !== "revealed") return;
  if (s.practiceIndex < s.practiceRound.length - 1) {
    app.set({ practiceIndex: s.practiceIndex + 1, practicePhase: { kind: "answering" } });
    return;
  }
  const score = s.practicePicks.filter((pick, i) => pick === s.practiceRound[i].answer).length;
  // The first finished round sets a best; it isn't "new" yet.
  const best = Math.max(s.bestScore ?? 0, score);
  if (best > 0) saveBestScore(best);
  app.set({
    practicePhase: { kind: "finished" },
    bestScore: best > 0 ? best : null,
    lastRoundWasNewBest: s.bestScore !== null && score > s.bestScore,
  });
}
