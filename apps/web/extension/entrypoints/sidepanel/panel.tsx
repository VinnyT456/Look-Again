import { ArrowUpRight, ImageUp, Link2, Lock, MousePointerClick, Settings, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { browser } from "wxt/browser";

import { WordmarkLockup } from "@/components/brand";
import { AnalyzingView, CropMarks, ResultsView } from "@/components/results";
import { Button, cx } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api/client";
import { parsePostLink } from "@/lib/bluesky/parse";
import { checkErrorMessages, genericCheckError } from "@/lib/models/errors";
import { verdictLabel } from "@/lib/models/verdict";
import { inMemoryImageUrl, isInMemoryImage, type VerificationCase } from "@/lib/models/verification-case";

import { onPending, takePending } from "../../lib/pending";
import { defaultExtensionSettings, loadExtensionSettings, onExtensionSettingsChange, type ExtensionSettings } from "../../lib/settings";

/*
 * The side panel mirrors the phone share sheet: a photo or post comes in
 * from the page, its result shows here, and Done discards it. Nothing is
 * kept unless the person opens the result in My Checks on the web app.
 */

/** What a check is run on; kept so Try again can repeat it. */
type Job = { kind: "image"; imageUrl: string } | { kind: "post"; link: string } | { kind: "file"; file: File };

type View =
  | { kind: "idle" }
  | { kind: "analyzing"; preview: string | null }
  | { kind: "result"; item: VerificationCase; src: string | null }
  | { kind: "failed"; message: string; job: Job };

type ServerStatus = "checking" | "ready" | "demo" | "unreachable";

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
/** Failures that trying the same thing again won't fix. */
const finalMessages = new Set<string>(
  (["invalidLink", "postNotFound", "noImage", "unreadablePhoto", "unsupported", "tooLarge"] as const).map((code) => checkErrorMessages[code]),
);
/** Right-click requests older than this were left behind by a closed panel. */
const PENDING_TTL = 60_000;

export function Panel() {
  const [settings, setSettings] = useState<ExtensionSettings | null>(null);
  const [view, setView] = useState<View>({ kind: "idle" });
  // The last answer about the detector, and which server gave it; a new server reads as "checking".
  const [probe, setProbe] = useState<{ server: string; status: Exclude<ServerStatus, "checking"> } | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [dragging, setDragging] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const upload = useRef<string | null>(null);
  const settingsRef = useRef<ExtensionSettings>(defaultExtensionSettings);
  const top = useRef<HTMLDivElement>(null);

  const dropUpload = () => {
    if (upload.current) URL.revokeObjectURL(upload.current);
    upload.current = null;
  };

  const run = useCallback(async (job: Job) => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    dropUpload();
    if (job.kind === "file") upload.current = URL.createObjectURL(job.file);
    const local = upload.current;
    setView({ kind: "analyzing", preview: job.kind === "image" ? job.imageUrl : local });
    setAnnouncement("Checking image");
    top.current?.scrollIntoView();

    const api = apiClient(settingsRef.current.server);
    try {
      let item =
        job.kind === "image"
          ? await api.checkImageUrl(job.imageUrl, current.signal)
          : job.kind === "post"
            ? await api.checkLink(job.link, current.signal)
            : await api.checkFile(job.file, current.signal);
      if (current.signal.aborted) return;
      // The server doesn't return uploads; this panel shows its own copy.
      if (job.kind === "file") item = { ...item, imageUrl: inMemoryImageUrl(item.id) };
      setView({ kind: "result", item, src: job.kind === "file" ? local : item.imageUrl });
      setAnnouncement(`${verdictLabel[item.verdict]}, ${item.confidencePercentage} percent confidence${item.isDemo ? ", demo result" : ""}`);
      setProbe({ server: settingsRef.current.server, status: item.isDemo ? "demo" : "ready" });
    } catch (error) {
      if (current.signal.aborted) return;
      dropUpload();
      setView({ kind: "failed", message: error instanceof ApiError ? error.message : genericCheckError, job });
      setAnnouncement("Couldn't check this image");
    } finally {
      if (controller.current === current) controller.current = null;
    }
  }, []);

  const checkFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return setView({ kind: "failed", message: checkErrorMessages.unsupported, job: { kind: "file", file } });
      if (file.size > MAX_UPLOAD_BYTES) return setView({ kind: "failed", message: checkErrorMessages.tooLarge, job: { kind: "file", file } });
      void run({ kind: "file", file });
    },
    [run],
  );

  const done = () => {
    controller.current?.abort();
    controller.current = null;
    dropUpload();
    setView({ kind: "idle" });
    setAnnouncement("");
  };

  // Settings first, then whatever the right-click menu asked for.
  useEffect(() => {
    let cancelled = false;
    const takeAndRun = async () => {
      const pending = await takePending();
      if (cancelled || !pending || Date.now() - pending.at > PENDING_TTL) return;
      void run(pending.kind === "image" ? { kind: "image", imageUrl: pending.imageUrl } : { kind: "post", link: pending.link });
    };
    void loadExtensionSettings().then((loaded) => {
      if (cancelled) return;
      settingsRef.current = loaded;
      setSettings(loaded);
      void takeAndRun();
    });
    const stopPending = onPending(() => void takeAndRun());
    const stopSettings = onExtensionSettingsChange((changed) => {
      settingsRef.current = changed;
      setSettings(changed);
    });
    return () => {
      cancelled = true;
      stopPending();
      stopSettings();
    };
  }, [run]);

  // Which detector answers, so the panel can say up front when results will be demos.
  const server = settings?.server;
  useEffect(() => {
    if (!server) return;
    let cancelled = false;
    apiClient(server)
      .detectorReady()
      .then((ready) => !cancelled && setProbe({ server, status: ready ? "ready" : "demo" }))
      .catch(() => !cancelled && setProbe({ server, status: "unreachable" }));
    return () => {
      cancelled = true;
    };
  }, [server]);
  const status: ServerStatus = probe && probe.server === server ? probe.status : "checking";

  // A copied image pasted anywhere in the panel is checked, as on the web.
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const file = [...(event.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
      if (!file) return;
      event.preventDefault();
      checkFile(file);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [checkFile]);

  const openInMyChecks = (item: VerificationCase) => {
    // Uploaded photos stay in this panel; the web app shows "Photo: Not included".
    const handoff = { ...item, imageUrl: item.imageUrl && isInMemoryImage(item.imageUrl) ? null : item.imageUrl };
    const bytes = new TextEncoder().encode(JSON.stringify(handoff));
    const encoded = btoa(Array.from(bytes, (byte) => String.fromCharCode(byte)).join(""));
    void browser.tabs.create({ url: `${settingsRef.current.server}/checks#import=${encoded}` });
  };

  return (
    <div
      className="flex min-h-dvh min-w-[300px] flex-col"
      onDragEnter={(event) => view.kind !== "analyzing" && event.dataTransfer.types.includes("Files") && setDragging(true)}
    >
      <div ref={top} />
      <header className="sticky top-0 z-20 flex min-h-13 items-center justify-between gap-3 bg-uv pr-1.5 pl-4 text-on-uv">
        <WordmarkLockup compact />
        <button
          type="button"
          onClick={() => void browser.runtime.openOptionsPage()}
          aria-label="Extension options"
          className="grid size-11 place-items-center rounded-md text-on-uv transition-colors duration-150 hover:bg-uv-active/60 focus-visible:outline-on-uv"
        >
          <Settings aria-hidden className="size-5" />
        </button>
      </header>

      <main className="flex flex-1 flex-col p-4">
        {view.kind === "idle" && <Idle status={status} server={settings?.server ?? null} onRun={run} onFile={checkFile} />}

        {view.kind === "analyzing" && <AnalyzingView preview={view.preview} onCancel={done} />}

        {view.kind === "failed" && (
          <Failed
            message={view.message}
            unreachable={status === "unreachable"}
            onRetry={finalMessages.has(view.message) ? null : () => void run(view.job)}
            onBack={done}
          />
        )}

        {view.kind === "result" && (
          <ResultsView key={view.item.id} item={view.item} imageSrc={view.src} showHeatmap={settings?.showHeatmap ?? true} inShareSheet />
        )}
      </main>

      {view.kind === "result" && (
        <footer className="sticky bottom-0 z-20 flex items-center gap-2 border-t border-rule bg-label/95 px-4 py-3 backdrop-blur-md">
          <Button variant="quiet" icon={ArrowUpRight} onClick={() => openInMyChecks(view.item)} className="-ml-2 px-2">
            Open in My Checks
          </Button>
          <Button onClick={done} className="ml-auto min-w-24">
            Done
          </Button>
        </footer>
      )}

      {dragging && (
        <div
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            const file = [...event.dataTransfer.files].find((f) => f.type.startsWith("image/"));
            if (file) checkFile(file);
          }}
          className="fixed inset-0 z-50 grid place-items-center bg-uv/80 p-4 backdrop-blur-[2px]"
        >
          <div className="pointer-events-none flex flex-col items-center gap-2 rounded-[3px] border-[1.5px] border-dashed border-on-uv-muted px-8 py-8 text-center text-on-uv">
            <ImageUp aria-hidden className="size-7" strokeWidth={1.75} />
            <p className="font-bold">Drop to check this photo</p>
          </div>
        </div>
      )}

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}

/** Before a check: the post on this tab, a link field, and a photo frame. */
function Idle({
  status,
  server,
  onRun,
  onFile,
}: {
  status: ServerStatus;
  server: string | null;
  onRun: (job: Job) => void;
  onFile: (file: File) => void;
}) {
  const tabPost = useActiveTabPost();
  const fileInput = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-title font-extrabold tracking-[-0.015em]">Check a photo</h1>
        <p className="mt-1.5 text-muted">See whether a photo on Bluesky is likely real or AI, before you share it.</p>
      </div>

      {status === "unreachable" && server && <ServerNotice server={server} />}

      {tabPost && (
        <section aria-labelledby="tab-post-title" className="rounded-[3px] border border-rule bg-label p-4">
          <p className="text-small text-muted">On this tab</p>
          <h2 id="tab-post-title" className="mt-0.5 truncate font-semibold">
            {tabPost.actor.startsWith("did:") ? "A Bluesky post" : `Post by @${tabPost.actor}`}
          </h2>
          <Button onClick={() => onRun({ kind: "post", link: tabPost.url })} className="mt-3 w-full">
            Check this post
          </Button>
        </section>
      )}

      <LinkField onSubmit={(link) => onRun({ kind: "post", link })} />

      <input
        ref={fileInput}
        type="file"
        accept="image/*"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) onFile(file);
        }}
      />
      <div className="grid place-items-center rounded-[3px] border border-rule bg-well px-4 py-8">
        <div className="relative flex flex-col items-center gap-2 px-6 py-4 text-center">
          <CropMarks detector={false} />
          <p className="font-bold">Drop or paste a photo</p>
          <p className="text-small text-pretty text-muted">Screenshots work too.</p>
          <Button variant="secondary" icon={ImageUp} onClick={() => fileInput.current?.click()} className="mt-1">
            Choose a photo
          </Button>
        </div>
      </div>

      <Tip>
        On Bluesky, right-click a photo and choose <span className="font-semibold text-ink">Check photo with WildcatVerify</span>.
      </Tip>

      <div className="mt-auto flex flex-col gap-2 border-t border-rule pt-4 text-small text-muted">
        <DetectorStatus status={status} />
        <p className="flex items-start gap-2">
          <Lock aria-hidden className="mt-0.5 size-3.5 shrink-0" />
          Private: photos are checked without being kept, and Done clears the result.
        </p>
      </div>
    </div>
  );
}

/** The Bluesky post open in this window's active tab, if any. */
function useActiveTabPost() {
  const [post, setPost] = useState<{ url: string; actor: string } | null>(null);
  useEffect(() => {
    const update = async () => {
      const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
      // The URL is only visible for sites the extension may read, which is bsky.app.
      const url = tab?.url;
      const parts = url && new URL(url).hostname === "bsky.app" ? parsePostLink(url) : null;
      setPost(url && parts ? { url, actor: parts.actor } : null);
    };
    const onUpdated = (_id: number, change: { url?: string; status?: string }) => (change.url || change.status === "complete") && void update();
    void update();
    browser.tabs.onActivated.addListener(update);
    browser.tabs.onUpdated.addListener(onUpdated);
    browser.windows.onFocusChanged.addListener(update);
    return () => {
      browser.tabs.onActivated.removeListener(update);
      browser.tabs.onUpdated.removeListener(onUpdated);
      browser.windows.onFocusChanged.removeListener(update);
    };
  }, []);
  return post;
}

function LinkField({ onSubmit }: { onSubmit: (link: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) onSubmit(value.trim());
      }}
    >
      <label htmlFor="post-link" className="mb-2 block font-semibold">
        Bluesky post link
      </label>
      <div className="flex min-h-12 items-center gap-2 rounded-md border border-rule-strong bg-label pr-1.5 pl-3 transition-colors focus-within:border-accent focus-within:outline-2 focus-within:outline-offset-0 focus-within:outline-accent/25">
        <Link2 aria-hidden className="size-[18px] shrink-0 text-muted" />
        <input
          id="post-link"
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          enterKeyHint="go"
          required
          placeholder="bsky.app/profile/…/post/…"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="min-w-0 flex-1 bg-transparent py-2.5 placeholder:text-muted focus:outline-none"
        />
        {value && (
          <button type="button" onClick={() => setValue("")} aria-label="Clear link" className="grid size-9 shrink-0 place-items-center rounded-md text-muted hover:text-ink">
            <X aria-hidden className="size-[18px]" />
          </button>
        )}
        <Button type="submit" className="min-h-9 px-3.5 py-1.5">
          Check
        </Button>
      </div>
    </form>
  );
}

function Tip({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-3 rounded-[3px] border border-rule bg-label px-4 py-3 text-small text-muted">
      <MousePointerClick aria-hidden className="mt-px size-[18px] shrink-0 text-accent" />
      <span>{children}</span>
    </p>
  );
}

function DetectorStatus({ status }: { status: ServerStatus }) {
  const text = {
    checking: "Checking detector…",
    ready: "Detector ready · CommunityForensics ViT",
    demo: "Detector offline: results are demos until it's back",
    unreachable: "Not connected to a WildcatVerify server",
  }[status];
  return (
    <p className="flex items-center gap-2">
      <span
        aria-hidden
        className={cx(
          "size-2 shrink-0 rounded-full",
          status === "ready" ? "bg-glow ring-1 ring-ink/25" : status === "checking" ? "bg-rule-strong/60" : "border border-muted",
        )}
      />
      {text}
    </p>
  );
}

function ServerNotice({ server }: { server: string }) {
  return (
    <div role="status" className="flex flex-col gap-2 rounded-[3px] border border-ai/40 bg-ai-wash px-4 py-3">
      <p>
        <span className="font-semibold text-ai">Can&apos;t reach WildcatVerify. </span>
        Nothing answered at <span className="font-medium break-all">{server.replace(/^https?:\/\//, "")}</span>.
      </p>
      <Button variant="secondary" icon={Settings} onClick={() => void browser.runtime.openOptionsPage()} className="self-start">
        Server settings
      </Button>
    </div>
  );
}

function Failed({ message, unreachable, onRetry, onBack }: { message: string; unreachable: boolean; onRetry: (() => void) | null; onBack: () => void }) {
  return (
    <div className="flex flex-col gap-4">
      <div role="alert" className="rounded-[3px] border border-ai/40 bg-ai-wash px-4 py-3">
        <p>
          <span className="font-semibold text-ai">Couldn&apos;t check this image. </span>
          {message}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {onRetry && <Button onClick={onRetry}>Try again</Button>}
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        {unreachable && (
          <Button variant="quiet" icon={Settings} onClick={() => void browser.runtime.openOptionsPage()}>
            Server settings
          </Button>
        )}
      </div>
    </div>
  );
}
