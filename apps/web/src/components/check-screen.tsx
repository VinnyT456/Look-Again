"use client";

import { ArrowRight, ImageUp, Link2, Lock, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { displayHandle, timeAgo } from "@/lib/models/verification-case";
import { app, cancelCheck, checkLink, checkPhoto, startNewCheck } from "@/lib/store/app";
import { imageSrc } from "@/lib/store/images";
import { useStore } from "@/lib/store/store";

import { Thumbnail } from "./history-screen";
import { AnalyzingView, CropMarks, ResultsView } from "./results";
import { PageHeader } from "./shell";
import { Button, cx, Ruled, SectionTitle, VerdictTag } from "./ui";

const hasFiles = (event: React.DragEvent) => event.dataTransfer.types.includes("Files");

/** The Check workspace: the intake (link or photo), then the bench while a check runs or its result. */
export function CheckScreen() {
  const path = useStore(app, (s) => s.checkPath);
  const analyzing = useStore(app, (s) => s.checkAnalyzing);
  const preview = useStore(app, (s) => s.checkPreview);
  const error = useStore(app, (s) => s.checkError);
  const showHeatmap = useStore(app, (s) => s.settings.showHeatmap);
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const top = path.at(-1);
  const idle = !analyzing && !top;
  const upload = () => fileInput.current?.click();

  // Pasting anywhere on the page checks a copied image.
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const file = [...(event.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
      if (file) {
        event.preventDefault();
        checkPhoto(file);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  return (
    <div onDragEnter={(event) => !analyzing && hasFiles(event) && setDragging(true)}>
      <PageHeader title="Check a photo" description="Paste a Bluesky post link or drop a photo to see whether it's likely real or AI." />

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
          if (file) checkPhoto(file);
        }}
      />

      {idle ? <Intake onUpload={upload} /> : <LinkBar onUpload={upload} />}

      {error && (
        <div role="alert" className="mt-3 flex items-start gap-3 rounded-[3px] border border-ai/40 bg-ai-wash px-4 py-3">
          <p className="flex-1">
            <span className="font-semibold text-ai">Couldn&apos;t check this image. </span>
            {error}
          </p>
          <button type="button" onClick={() => app.set({ checkError: null })} aria-label="Dismiss" className="-m-1.5 grid size-9 place-items-center rounded-md text-muted hover:text-ink">
            <X aria-hidden className="size-[18px]" />
          </button>
        </div>
      )}

      {analyzing ? (
        <div className="mt-6">
          <AnalyzingView preview={preview} onCancel={cancelCheck} />
        </div>
      ) : top ? (
        <div className="mt-6">
          <ResultsView key={top.id} item={top} imageSrc={imageSrc(top.imageUrl)} showHeatmap={showHeatmap} onCheckAnother={startNewCheck} />
        </div>
      ) : (
        <RecentChecks />
      )}

      {dragging && (
        <div
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            const file = [...event.dataTransfer.files].find((f) => f.type.startsWith("image/"));
            if (file) checkPhoto(file);
          }}
          className="fixed inset-0 z-50 grid place-items-center bg-uv/80 p-6 backdrop-blur-[2px]"
        >
          <div className="pointer-events-none flex flex-col items-center gap-3 rounded-[3px] border-[1.5px] border-dashed border-on-uv-muted px-12 py-10 text-center text-on-uv">
            <ImageUp aria-hidden className="size-8" strokeWidth={1.75} />
            <p className="text-title font-extrabold">Drop to check this photo</p>
            <p className="text-on-uv-muted">It&apos;s checked right away and isn&apos;t kept on the server.</p>
          </div>
        </div>
      )}
    </div>
  );
}

/** The post link field, with Check inside it. */
function LinkField({ large = false }: { large?: boolean }) {
  const input = useStore(app, (s) => s.checkInput);
  const analyzing = useStore(app, (s) => s.checkAnalyzing);

  return (
    <form
      className="min-w-0 flex-1"
      onSubmit={(event) => {
        event.preventDefault();
        checkLink();
      }}
    >
      <label htmlFor="post-link" className={cx("mb-2 block font-semibold", !large && "sr-only")}>
        Bluesky post link
      </label>
      <div
        className={cx(
          "flex items-center gap-2 rounded-md border border-rule-strong bg-label pr-1.5 pl-3.5 transition-colors focus-within:border-accent focus-within:outline-2 focus-within:outline-offset-0 focus-within:outline-accent/25",
          large ? "min-h-14" : "min-h-12",
        )}
      >
        <Link2 aria-hidden className="size-[18px] shrink-0 text-muted" />
        <input
          id="post-link"
          type="url"
          inputMode="url"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="go"
          required
          placeholder="https://bsky.app/profile/…/post/…"
          value={input}
          onChange={(event) => app.set({ checkInput: event.target.value })}
          className="min-w-0 flex-1 bg-transparent py-2.5 placeholder:text-muted focus:outline-none"
        />
        {input && (
          <button type="button" onClick={() => app.set({ checkInput: "" })} aria-label="Clear link" className="grid size-9 shrink-0 place-items-center rounded-md text-muted hover:text-ink">
            <X aria-hidden className="size-[18px]" />
          </button>
        )}
        <Button type="submit" disabled={analyzing} className={cx("min-h-10 py-2", large && "min-h-11 px-5")}>
          Check
        </Button>
      </div>
    </form>
  );
}

/** Before a check: the link field, then a drop frame for a photo, in one sheet. */
function Intake({ onUpload }: { onUpload: () => void }) {
  const keepHistory = useStore(app, (s) => s.settings.keepHistory);
  return (
    <section aria-label="Start a check" className="rounded-[3px] border border-rule bg-label">
      <div className="p-4 sm:p-6">
        <LinkField large />
      </div>

      <div aria-hidden className="flex items-center gap-4 px-4 text-small font-semibold text-muted sm:px-6">
        <span className="h-px flex-1 bg-rule" />
        or
        <span className="h-px flex-1 bg-rule" />
      </div>

      <div className="p-4 sm:p-6">
        <div className="grid min-h-[min(320px,42dvh)] place-items-center bg-well px-6 py-12 pointer-coarse:min-h-0 pointer-coarse:py-6">
          <div className="relative flex max-w-[46ch] flex-col items-center gap-3 px-8 py-6 text-center">
            <CropMarks detector={false} />
            <p className="font-bold">
              <span className="pointer-coarse:hidden">Drop a photo or screenshot anywhere</span>
              <span className="hidden pointer-coarse:inline">Check a photo from your device</span>
            </p>
            <p className="text-pretty text-muted pointer-coarse:hidden">
              Or paste one with <Kbd>Ctrl</Kbd> <Kbd>V</Kbd> (<Kbd>⌘</Kbd> <Kbd>V</Kbd> on a Mac).
            </p>
            <Button variant="secondary" icon={ImageUp} onClick={onUpload} className="mt-2">
              Choose a photo
            </Button>
          </div>
        </div>
      </div>

      <p className="flex items-start gap-2.5 border-t border-rule px-4 py-3.5 text-small text-muted sm:px-6">
        <Lock aria-hidden className="mt-0.5 size-3.5 shrink-0" />
        {keepHistory ? "Checks are saved in this browser. You can change that in Settings." : "Private: the WildcatVerify server checks photos without keeping them, and My Checks clears when you close this tab."}
      </p>
    </section>
  );
}

function Kbd({ children }: { children: string }) {
  return <kbd className="rounded-[3px] border border-rule-strong bg-label px-1.5 py-px font-sans text-small font-semibold text-ink">{children}</kbd>;
}

/** With a check on the bench: the link field and Upload a photo, in one bar. */
function LinkBar({ onUpload }: { onUpload: () => void }) {
  const analyzing = useStore(app, (s) => s.checkAnalyzing);
  return (
    <div className="flex flex-col gap-2 sm:flex-row">
      <LinkField />
      <Button variant="secondary" icon={ImageUp} onClick={onUpload} disabled={analyzing} className="min-h-12">
        Upload a photo
      </Button>
    </div>
  );
}

/** The last few checks, so a result is one click away after starting over. */
function RecentChecks() {
  const router = useRouter();
  const cases = useStore(app, (s) => s.cases);
  if (cases.length === 0) return null;

  return (
    <section aria-labelledby="recent-title" className="mt-10">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <SectionTitle id="recent-title">Recent checks</SectionTitle>
        <Link href="/checks" className="inline-flex items-center gap-1.5 text-small font-semibold text-accent hover:underline">
          All of My Checks
          <ArrowRight aria-hidden className="size-3.5" />
        </Link>
      </div>
      <Ruled className="rounded-[3px] border border-rule bg-label">
        {cases.slice(0, 3).map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              app.set({ historyPath: [item] });
              router.push("/checks");
            }}
            className="flex w-full items-center gap-4 px-4 py-3 text-left transition-colors duration-150 hover:bg-well focus-visible:-outline-offset-2"
          >
            <Thumbnail item={item} />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{item.title}</span>
              <span className="block truncate text-small text-muted" suppressHydrationWarning>
                {displayHandle(item)} · {timeAgo(item)}
              </span>
            </span>
            <VerdictTag verdict={item.verdict} />
          </button>
        ))}
      </Ruled>
    </section>
  );
}
