"use client";

import { ArrowUpRight, ChevronRight, LoaderCircle, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, type ReactNode } from "react";

import { verdictLabel, type VerdictType } from "@/lib/models/verdict";

import { verdictIcon, verdictTone } from "./icons";

/*
 * Building blocks of the condition report: label-stock panels with ruled
 * rows, plain buttons, and the verdict mark.
 */

const cx = (...classes: (string | false | null | undefined)[]) => classes.filter(Boolean).join(" ");
export { cx };

/** A heading for a group of rows or a panel. */
export function SectionTitle({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <h2 id={id} className="font-bold tracking-[-0.005em] text-ink">
      {children}
    </h2>
  );
}

/** One sheet of label stock with its title; on wide screens the title and note sit in a column beside it. */
export function Panel({ title, footer, className, children }: { title?: ReactNode; footer?: ReactNode; className?: string; children: ReactNode }) {
  return (
    <section className={cx("grid gap-x-10 gap-y-2 lg:grid-cols-[260px_minmax(0,1fr)]", className)}>
      <div className="flex flex-col gap-1 lg:pt-3">
        {title && <SectionTitle>{title}</SectionTitle>}
        {footer && <p className="hidden max-w-[65ch] text-small text-pretty text-muted lg:block">{footer}</p>}
      </div>
      <div className="rounded-[3px] border border-rule bg-label">{children}</div>
      {footer && <p className="max-w-[65ch] text-small text-muted lg:hidden">{footer}</p>}
    </section>
  );
}

/** Rows separated by 1px rules. */
export function Ruled({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cx("divide-y divide-rule", className)}>{children}</div>;
}

const rowClass = "flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left";
const pressable = "transition-colors duration-150 hover:bg-well focus-visible:-outline-offset-2";

/** "Label ……… value". */
export function ValueRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className={rowClass}>
      <span className="flex-1 text-muted">{label}</span>
      <span className="line-clamp-2 text-right font-medium">{value}</span>
    </div>
  );
}

/** An internal route, or an external page opened in a new tab. */
export function LinkRow({ title, href, subtitle, icon: Icon }: { title: string; href: string; subtitle?: string; icon?: LucideIcon }) {
  const external = /^https?:/.test(href);
  const body = (
    <>
      {Icon && <Icon aria-hidden className="size-5 shrink-0 text-accent" />}
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{title}</span>
        {subtitle && <span className="block text-small text-muted">{subtitle}</span>}
      </span>
      {external ? (
        <ArrowUpRight aria-label="Opens in a new tab" className="size-[18px] shrink-0 text-muted" />
      ) : (
        <ChevronRight aria-hidden className="size-[18px] shrink-0 text-muted" />
      )}
    </>
  );
  return external ? (
    <a href={href} target="_blank" rel="noreferrer" className={cx(rowClass, pressable)}>
      {body}
    </a>
  ) : (
    <Link href={href} className={cx(rowClass, pressable)}>
      {body}
    </Link>
  );
}

export function ToggleRow({ title, detail, checked, onChange }: { title: string; detail?: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} className={cx(rowClass, pressable, "items-start")}>
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{title}</span>
        {detail && <span className="block max-w-[60ch] text-small text-muted">{detail}</span>}
      </span>
      <span aria-hidden className={cx("relative mt-0.5 h-6 w-10 shrink-0 rounded-full border transition-colors duration-200", checked ? "border-uv bg-uv dark:border-accent dark:bg-accent" : "border-rule-strong bg-well")}>
        <span
          className={cx(
            "absolute top-[3px] left-[3px] size-4 rounded-full transition-transform duration-200 ease-out-expo",
            checked ? "translate-x-4 bg-label" : "bg-muted",
          )}
        />
      </span>
    </button>
  );
}

type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";

const buttonVariant: Record<ButtonVariant, string> = {
  primary: "border-uv bg-uv text-on-uv hover:bg-uv-active dark:border-accent dark:bg-accent dark:text-wall dark:hover:bg-accent/85",
  secondary: "border-rule-strong bg-label text-ink hover:bg-well",
  quiet: "border-transparent text-accent hover:bg-well",
  danger: "border-rule-strong bg-label text-ai hover:bg-ai-wash",
};

export const buttonClass = (variant: ButtonVariant = "primary", className?: string) =>
  cx(
    "inline-flex min-h-11 items-center justify-center gap-2 rounded-md border px-4 py-2.5 font-semibold transition-colors duration-150",
    "disabled:cursor-default disabled:border-rule disabled:bg-well disabled:text-muted",
    buttonVariant[variant],
    className,
  );

export function Button({
  variant = "primary",
  icon: Icon,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; icon?: LucideIcon }) {
  return (
    <button type="button" {...props} className={buttonClass(variant, className)}>
      {Icon && <Icon aria-hidden className="size-[18px] shrink-0" />}
      {children}
    </button>
  );
}

const markSize = { sm: "size-6 [&>svg]:size-3.5", md: "size-9 [&>svg]:size-[18px]", lg: "size-12 [&>svg]:size-6" };

/** The verdict mark: one filled disc and glyph, the same object at every size. Always paired with words. */
export function VerdictMark({ verdict, size = "md" }: { verdict: VerdictType; size?: keyof typeof markSize }) {
  const Icon = verdictIcon[verdict];
  return (
    <span aria-hidden className={cx("grid shrink-0 place-items-center rounded-full text-label", verdictTone[verdict].solid, markSize[size])}>
      <Icon strokeWidth={2.5} />
    </span>
  );
}

/** Small mark plus the one-word verdict, for rows and tiles. */
export function VerdictTag({ verdict, className }: { verdict: VerdictType; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-2 font-semibold", verdictTone[verdict].ink, className)}>
      <VerdictMark verdict={verdict} size="sm" />
      {verdictLabel[verdict]}
    </span>
  );
}

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return <LoaderCircle aria-label={label} aria-hidden={!label} className={cx("animate-spin text-muted", className ?? "size-6")} />;
}

/** Empty or error state: icon, title, description and an optional action. */
export function EmptyState({
  title,
  icon: Icon,
  description,
  action,
}: {
  title: string;
  icon: LucideIcon;
  description?: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-[3px] border border-rule bg-label px-6 py-14 text-center">
      <span className="mb-2 grid size-12 place-items-center rounded-md bg-well text-accent">
        <Icon aria-hidden className="size-6" strokeWidth={1.75} />
      </span>
      <h2 className="font-bold">{title}</h2>
      {description && <p className="max-w-[48ch] text-pretty text-muted">{description}</p>}
      {action && (
        <Button onClick={action.onClick} className="mt-3">
          {action.label}
        </Button>
      )}
    </div>
  );
}

/** A row of mutually exclusive options on one track. */
export function Segmented<T extends string>({
  options,
  value,
  label,
  onChange,
  ariaLabel,
  className,
}: {
  options: readonly T[];
  value: T;
  label: (option: T) => string;
  onChange: (option: T) => void;
  ariaLabel: string;
  className?: string;
}) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className={cx("inline-flex rounded-lg border border-rule bg-label p-1", className)}>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={option === value}
          onClick={() => onChange(option)}
          className={cx(
            "min-h-9 flex-1 rounded-md px-3.5 text-small font-semibold whitespace-nowrap transition-colors duration-150",
            option === value ? "bg-uv text-on-uv dark:bg-accent dark:text-wall" : "text-muted hover:bg-well hover:text-ink",
          )}
        >
          {label(option)}
        </button>
      ))}
    </div>
  );
}

/** A native modal dialog; Escape and the backdrop close it. */
export function Dialog({
  open,
  onClose,
  labelledBy,
  className,
  children,
}: {
  open: boolean;
  onClose: () => void;
  labelledBy: string;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={labelledBy}
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose()}
      className={cx(
        "m-auto max-h-[calc(100dvh-32px)] w-[calc(100%-32px)] overflow-y-auto rounded-[3px] border border-rule bg-label text-ink shadow-[0_18px_48px_rgb(0_0_0/0.28)] backdrop:bg-uv/55",
        className ?? "max-w-[400px]",
      )}
    >
      {open && children}
    </dialog>
  );
}

/** Confirms a destructive action. */
export function ConfirmDialog({
  open,
  title,
  message,
  confirm,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirm: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Dialog open={open} onClose={onCancel} labelledBy="confirm-title">
      <div className="flex flex-col gap-2 p-6">
        <h2 id="confirm-title" className="font-semibold">
          {title}
        </h2>
        <p className="text-muted">{message}</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirm}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
