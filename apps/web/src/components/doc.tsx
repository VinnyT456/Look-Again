import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

/** A long-form page reached from Settings: Privacy Policy, Credits. */
export function DocPage({ title, intro, children }: { title: string; intro: ReactNode; children: ReactNode }) {
  return (
    <article className="max-w-[760px]">
      <Link href="/settings" className="-ml-2 mb-5 inline-flex min-h-11 items-center gap-2 rounded-md px-2 font-semibold text-accent transition-colors hover:bg-label">
        <ArrowLeft aria-hidden className="size-[18px]" />
        Settings
      </Link>
      <header className="mb-6">
        <h1 className="text-title font-extrabold tracking-[-0.01em]">{title}</h1>
        <p className="mt-1 max-w-[65ch] text-muted">{intro}</p>
      </header>
      <div className="divide-y divide-rule rounded-[3px] border border-rule bg-label">{children}</div>
    </article>
  );
}

export function DocSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2 px-5 py-5 [&_p]:max-w-[65ch]">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export function DocLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="font-semibold text-accent underline underline-offset-4">
      {children}
    </a>
  );
}
