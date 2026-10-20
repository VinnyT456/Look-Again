"use client";

import { ArrowLeft, GraduationCap, LayoutGrid, ListChecks, ScanSearch, Settings, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { app, hydrate } from "@/lib/store/app";
import { useStore } from "@/lib/store/store";

import { WordmarkLockup } from "./brand";
import { cx } from "./ui";

interface Section {
  href: string;
  title: string;
  icon: LucideIcon;
}

const sections: Section[] = [
  { href: "/", title: "Check", icon: ScanSearch },
  { href: "/feed", title: "Feed", icon: LayoutGrid },
  { href: "/checks", title: "My Checks", icon: ListChecks },
  { href: "/learn", title: "Learn", icon: GraduationCap },
];
const settings: Section = { href: "/settings", title: "Settings", icon: Settings };

const isActive = (section: Section, pathname: string) => (section.href === "/" ? pathname === "/" : pathname.startsWith(section.href));

/** The UV-violet rail on wide screens; a top bar and a bottom tab bar on narrow ones. */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const announcement = useStore(app, (s) => s.announcement);

  useEffect(() => {
    void hydrate();
  }, []);

  return (
    <div className="lg:grid lg:grid-cols-[240px_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-label px-4 py-2.5 font-semibold text-ink focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>

      <aside className="sticky top-0 z-30 bg-uv text-on-uv lg:flex lg:h-dvh lg:flex-col lg:px-4 lg:py-6">
        <div className="flex min-h-14 items-center justify-between gap-4 px-4 lg:block lg:min-h-0 lg:px-2">
          <Wordmark />
          <Link
            href={settings.href}
            aria-label="Settings"
            aria-current={isActive(settings, pathname) ? "page" : undefined}
            className={cx(
              "-mr-2 grid size-11 place-items-center rounded-md transition-colors duration-150 focus-visible:outline-on-uv lg:hidden",
              isActive(settings, pathname) ? "bg-uv-active text-white" : "text-on-uv hover:bg-uv-active/60",
            )}
          >
            <Settings aria-hidden className="size-5" />
          </Link>
        </div>

        <nav aria-label="Main" className="mt-8 hidden flex-col gap-1 lg:flex">
          {sections.map((section) => (
            <RailLink key={section.href} section={section} active={isActive(section, pathname)} />
          ))}
        </nav>

        <RailFoot active={isActive(settings, pathname)} />
      </aside>

      <main id="main" tabIndex={-1} className="min-w-0 px-4 pt-6 pb-28 focus:outline-none sm:px-6 lg:px-10 lg:pt-8 lg:pb-16">
        <div className="max-w-[1180px]">{children}</div>
      </main>

      <TabBar pathname={pathname} />

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}

/** The wordmark with its specimen mark. */
function Wordmark() {
  return (
    <Link href="/" className="-mx-1 inline-flex rounded-sm px-1 focus-visible:outline-on-uv">
      <WordmarkLockup />
    </Link>
  );
}

function RailLink({ section, active }: { section: Section; active: boolean }) {
  const unseen = useStore(app, (s) => s.unseen);
  const Icon = section.icon;
  return (
    <Link
      href={section.href}
      aria-current={active ? "page" : undefined}
      className={cx(
        "flex min-h-11 items-center gap-3 rounded-md px-3 transition-colors duration-150 focus-visible:outline-on-uv",
        active ? "bg-uv-active font-semibold text-white" : "font-medium text-on-uv hover:bg-uv-active/60",
      )}
    >
      <Icon aria-hidden className={cx("size-[18px] shrink-0", active ? "text-white" : "text-on-uv-muted")} />
      <span className="flex-1">{section.title}</span>
      {section.href === "/checks" && unseen > 0 && <UnseenCount count={unseen} className="bg-on-uv text-uv" />}
    </Link>
  );
}

function UnseenCount({ count, className }: { count: number; className?: string }) {
  return (
    <span className={cx("grid h-5 min-w-5 place-items-center rounded-full px-1.5 text-[12px] leading-none font-bold tabular-nums", className)}>
      <span aria-hidden>{count}</span>
      <span className="sr-only">{count} new</span>
    </span>
  );
}

/** Detector status, Settings and the privacy promise, at the foot of the rail. */
function RailFoot({ active }: { active: boolean }) {
  const ready = useStore(app, (s) => s.detectorReady);
  const keepHistory = useStore(app, (s) => s.settings.keepHistory);
  return (
    <div className="mt-auto hidden flex-col gap-4 lg:flex">
      <div className="rounded-md border border-on-uv/15 px-3 py-3 text-small">
        <p className="flex items-center gap-2 font-semibold text-on-uv">
          <span aria-hidden className={cx("size-2 shrink-0 rounded-full", ready ? "bg-glow" : ready === false ? "border border-on-uv-muted" : "bg-on-uv-muted/40")} />
          {ready === null ? "Checking detector…" : ready ? "Detector ready" : "Detector offline"}
        </p>
        <p className="mt-0.5 pl-4 text-on-uv-muted">{ready === false ? "Results are demos until it's back." : "CommunityForensics ViT"}</p>
        <p className="mt-2 border-t border-on-uv/15 pt-2 text-on-uv-muted">{keepHistory ? "Checks kept in this browser" : "Private: photos aren't stored"}</p>
      </div>
      <RailLink section={settings} active={active} />
    </div>
  );
}

/** The four sections as a bottom tab bar on narrow screens, like the phone apps. */
function TabBar({ pathname }: { pathname: string }) {
  const unseen = useStore(app, (s) => s.unseen);
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-rule bg-label/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md lg:hidden"
    >
      {sections.map((section) => {
        const active = isActive(section, pathname);
        const Icon = section.icon;
        return (
          <Link
            key={section.href}
            href={section.href}
            aria-current={active ? "page" : undefined}
            className={cx(
              "relative flex min-h-14 flex-col items-center justify-center gap-0.5 text-[12px] leading-4 transition-colors duration-150 focus-visible:-outline-offset-2",
              active ? "font-bold text-accent" : "font-medium text-muted hover:text-ink",
            )}
          >
            <Icon aria-hidden className="size-[22px]" strokeWidth={active ? 2.25 : 1.75} />
            {section.title}
            {section.href === "/checks" && unseen > 0 && <UnseenCount count={unseen} className="absolute top-1.5 left-[calc(50%+6px)] bg-accent text-label" />}
          </Link>
        );
      })}
    </nav>
  );
}

/** A screen's title, with its actions trailing. */
export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end gap-x-6 gap-y-3 lg:mb-8">
      <div className="min-w-0 flex-1">
        <h1 className="text-title font-extrabold tracking-[-0.015em] text-balance">{title}</h1>
        {description && <p className="mt-1.5 max-w-[65ch] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

/** Back to the list a result was opened from, plus actions for the result. */
export function BackBar({ label, onBack, actions }: { label: string; onBack: () => void; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex items-center gap-3">
      <button type="button" onClick={onBack} className="-ml-2 inline-flex min-h-11 items-center gap-2 rounded-md px-2 font-semibold text-accent transition-colors hover:bg-label">
        <ArrowLeft aria-hidden className="size-[18px]" />
        {label}
      </button>
      {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
    </div>
  );
}
