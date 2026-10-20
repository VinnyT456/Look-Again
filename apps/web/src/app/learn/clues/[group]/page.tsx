import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { clueIcon } from "@/components/icons";
import { clueGuide } from "@/lib/learn/clues";

export const generateStaticParams = () => clueGuide.map((group) => ({ group: group.id }));

export async function generateMetadata({ params }: PageProps<"/learn/clues/[group]">): Promise<Metadata> {
  const { group: id } = await params;
  return { title: clueGuide.find((group) => group.id === id)?.title ?? "Clue Guide" };
}

/** One group of the Clue Guide: each clue with what to look for. */
export default async function ClueGroupPage({ params }: PageProps<"/learn/clues/[group]">) {
  const { group: id } = await params;
  const group = clueGuide.find((candidate) => candidate.id === id);
  if (!group) notFound();

  return (
    <div className="max-w-[880px]">
      <Link href="/learn" className="-ml-2 mb-5 inline-flex min-h-11 items-center gap-2 rounded-md px-2 font-semibold text-accent transition-colors hover:bg-label">
        <ArrowLeft aria-hidden className="size-[18px]" />
        Learn
      </Link>
      <header className="mb-6">
        <h1 className="text-title font-extrabold tracking-[-0.01em]">{group.title}</h1>
        <p className="mt-1 max-w-[65ch] text-muted">{group.summary}.</p>
      </header>

      <ol className="divide-y divide-rule rounded-[3px] border border-rule bg-label">
        {group.clues.map((clue) => {
          const Icon = clueIcon[clue.icon];
          return (
            <li key={clue.title} className="flex gap-4 px-5 py-4">
              <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
              <div>
                <h2 className="font-semibold">{clue.title}</h2>
                <p className="mt-0.5 max-w-[65ch] text-muted">{clue.detail}</p>
              </div>
            </li>
          );
        })}
      </ol>

      <nav aria-label="Other clue groups" className="mt-8 flex flex-wrap gap-2">
        {clueGuide
          .filter((other) => other.id !== group.id)
          .map((other) => (
            <Link key={other.id} href={`/learn/clues/${other.id}`} className="inline-flex min-h-11 items-center rounded-md border border-rule-strong bg-label px-4 font-semibold transition-colors hover:bg-well">
              {other.title}
            </Link>
          ))}
      </nav>
    </div>
  );
}
