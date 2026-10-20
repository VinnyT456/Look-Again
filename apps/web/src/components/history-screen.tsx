"use client";

import { ListChecks, ListFilter, Search, SearchX, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { verdictFilters, verdictFilterTitle } from "@/lib/models/verdict";
import { displayHandle, timeAgo, type VerificationCase } from "@/lib/models/verification-case";
import { app, clearCases, markSeen, removeCase, startNewCheck } from "@/lib/store/app";
import { imageSrc } from "@/lib/store/images";
import { useStore } from "@/lib/store/store";

import { ResultsView } from "./results";
import { BackBar, PageHeader } from "./shell";
import { Button, ConfirmDialog, EmptyState, Segmented, VerdictMark, VerdictTag } from "./ui";

/** Every check the user ran, as a register: searchable, filterable by verdict, with delete. */
export function HistoryScreen() {
  const router = useRouter();
  const hydrated = useStore(app, (s) => s.hydrated);
  const cases = useStore(app, (s) => s.cases);
  const unseen = useStore(app, (s) => s.unseen);
  const path = useStore(app, (s) => s.historyPath);
  const query = useStore(app, (s) => s.historyQuery);
  const filter = useStore(app, (s) => s.historyFilter);
  const showHeatmap = useStore(app, (s) => s.settings.showHeatmap);
  const keepHistory = useStore(app, (s) => s.settings.keepHistory);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const top = path.at(-1);

  useEffect(() => {
    if (unseen > 0) markSeen();
  }, [unseen]);

  if (top) {
    return (
      <div>
        <BackBar label="My Checks" onBack={() => app.set({ historyPath: path.slice(0, -1) })} />
        <ResultsView
          key={top.id}
          item={top}
          imageSrc={imageSrc(top.imageUrl)}
          showHeatmap={showHeatmap}
          onCheckAnother={() => {
            startNewCheck();
            router.push("/");
          }}
        />
      </div>
    );
  }

  const trimmed = query.trim().toLowerCase();
  const visible = cases.filter(
    (item) =>
      (filter === "all" || item.verdict === filter) &&
      (!trimmed || [item.authorHandle, item.title, item.caption].some((field) => field.toLowerCase().includes(trimmed))),
  );

  return (
    <div>
      <PageHeader
        title="My Checks"
        description={keepHistory ? "Saved in this browser only." : "Kept until you close this tab. Turn on Keep My Checks in Settings to save them in this browser."}
        actions={
          cases.length > 0 && (
            <Button variant="danger" icon={Trash2} onClick={() => setConfirmingClear(true)}>
              Clear all
            </Button>
          )
        }
      />

      {cases.length > 0 && (
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3.5 size-[18px] -translate-y-1/2 text-muted" />
            <input
              type="search"
              aria-label="Search by author or topic"
              placeholder="Search by author or topic"
              value={query}
              onChange={(event) => app.set({ historyQuery: event.target.value })}
              className="min-h-11 w-full rounded-md border border-rule bg-label pr-10 pl-10 placeholder:text-muted focus:border-accent focus:outline-none [&::-webkit-search-cancel-button]:hidden"
            />
            {query && (
              <button type="button" aria-label="Clear search" onClick={() => app.set({ historyQuery: "" })} className="absolute inset-y-0 right-0 grid w-10 place-items-center text-muted hover:text-ink">
                <X aria-hidden className="size-[18px]" />
              </button>
            )}
          </div>
          <Segmented ariaLabel="Filter by verdict" options={verdictFilters} value={filter} label={verdictFilterTitle} onChange={(option) => app.set({ historyFilter: option })} />
        </div>
      )}

      {visible.length > 0 && (
        <div className="overflow-hidden rounded-[3px] border border-rule bg-label">
          <table className="w-full border-collapse text-left">
            <thead className="text-small text-muted">
              <tr className="border-b border-rule">
                <th scope="col" className="w-[76px] py-2.5 pl-4 font-semibold">
                  <span className="sr-only">Photo</span>
                </th>
                <th scope="col" className="py-2.5 pr-4 font-semibold">
                  Post
                </th>
                <th scope="col" className="py-2.5 pr-4 font-semibold md:w-[160px]">
                  Verdict
                </th>
                <th scope="col" className="hidden w-[120px] py-2.5 pr-4 text-right font-semibold md:table-cell">
                  Confidence
                </th>
                <th scope="col" className="hidden w-[150px] py-2.5 pr-4 font-semibold md:table-cell">
                  Checked
                </th>
                <th scope="col" className="w-14">
                  <span className="sr-only">Delete</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <RegisterRow key={item.id} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {hydrated &&
        visible.length === 0 &&
        (cases.length === 0 ? (
          <EmptyState
            title="No checks yet"
            icon={ListChecks}
            description="Paste a Bluesky link or drop a photo on the Check page. Each result is entered here."
            action={{ label: "Check a photo", onClick: () => router.push("/") }}
          />
        ) : !query ? (
          <EmptyState title={`No ${verdictFilterTitle(filter)} checks`} icon={ListFilter} description="Try a different filter." />
        ) : (
          <EmptyState title={`No results for “${query}”`} icon={SearchX} description="Check the spelling or try a new search." />
        ))}

      <ConfirmDialog
        open={confirmingClear}
        title="Clear all checks?"
        message="This removes every check and uploaded photo from this browser."
        confirm="Clear all"
        onCancel={() => setConfirmingClear(false)}
        onConfirm={() => {
          setConfirmingClear(false);
          clearCases();
        }}
      />
    </div>
  );
}

/** One entry: the whole row opens the result; the bin deletes it. */
function RegisterRow({ item }: { item: VerificationCase }) {
  const when = item.isDemo ? `${timeAgo(item)} · Demo` : timeAgo(item);
  return (
    <tr className="relative border-b border-rule transition-colors last:border-b-0 hover:bg-well">
      <td className="py-2.5 pl-4">
        <Thumbnail item={item} />
      </td>
      <td className="max-w-0 py-2.5 pr-4">
        <button type="button" onClick={() => app.set({ historyPath: [item] })} className="block w-full text-left after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:-outline-offset-2 focus-visible:after:outline-accent">
          <span className="line-clamp-1 font-semibold">{item.title}</span>
          <span className="block truncate text-small text-muted">
            {displayHandle(item)}
            <span className="md:hidden" suppressHydrationWarning>
              {" "}
              · {item.confidencePercentage}% · {when}
            </span>
          </span>
        </button>
      </td>
      <td className="py-2.5 pr-4 whitespace-nowrap">
        <VerdictTag verdict={item.verdict} />
      </td>
      <td className="hidden py-2.5 pr-4 text-right font-medium tabular-nums md:table-cell">{item.confidencePercentage}%</td>
      <td className="hidden py-2.5 pr-4 whitespace-nowrap text-muted md:table-cell" suppressHydrationWarning>
        {when}
      </td>
      <td className="py-2.5 pr-2">
        <button
          type="button"
          onClick={() => removeCase(item)}
          aria-label={`Delete check: ${item.title}`}
          title="Delete"
          className="relative z-10 grid size-10 place-items-center rounded-md text-muted transition-colors hover:bg-ai-wash hover:text-ai"
        >
          <Trash2 aria-hidden className="size-[18px]" />
        </button>
      </td>
    </tr>
  );
}

/** The case's photo, or its verdict mark so rows stay scannable by result. */
export function Thumbnail({ item }: { item: VerificationCase }) {
  const [failed, setFailed] = useState(false);
  const src = imageSrc(item.imageUrl);
  return (
    <span className="grid size-12 place-items-center overflow-hidden rounded-[2px] bg-well">
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element -- remote Bluesky CDN images and in-memory uploads
        <img src={src} alt="" onError={() => setFailed(true)} className="size-full object-cover" loading="lazy" />
      ) : (
        <VerdictMark verdict={item.verdict} />
      )}
    </span>
  );
}
