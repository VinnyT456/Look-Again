"use client";

import { ArrowRight, Check, ChevronDown, ChevronRight, Image as ImageIcon, Reply, RotateCcw, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { clueGuide, groupFor } from "@/lib/learn/clues";
import {
  answerDefinition,
  answerInSentence,
  answerLabel,
  answerPhrase,
  guideFocus,
  missesOf,
  mostMissed,
  practiceAnswers,
  reviewTitle,
  roundSummary,
  type Miss,
  type PracticeAnswer,
  type PracticeQuestion,
} from "@/lib/learn/practice";
import { app, nextQuestion, restartPractice, selectAnswer } from "@/lib/store/app";
import { useStore } from "@/lib/store/store";

import { clueIcon } from "./icons";
import { PageHeader } from "./shell";
import { Button, cx, Dialog, SectionTitle } from "./ui";

/** Learn to spot fakes: a Look Again round played in place, beside the clue guide. */
export function LearnScreen() {
  return (
    <div>
      <PageHeader title="Learn" description="Practice the habit the detector can't replace: looking again before you share." />
      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <PracticeRound />
        <ClueIndex />
      </div>
    </div>
  );
}

/** Look Again: read the post, answer, see why, next. */
function PracticeRound() {
  const round = useStore(app, (s) => s.practiceRound);
  const index = useStore(app, (s) => s.practiceIndex);
  const picks = useStore(app, (s) => s.practicePicks);
  const phase = useStore(app, (s) => s.practicePhase);
  const answerCount = useStore(app, (s) => s.practiceAnswerCount);
  const card = useRef<HTMLDivElement>(null);
  const answers = useRef<HTMLDivElement>(null);
  const question = round[index];
  const inProgress = phase.kind !== "finished" && (picks.length > 0 || index > 0);
  const picked = phase.kind === "revealed" ? phase.picked : null;
  const isLast = index >= round.length - 1;

  const scrollTo = (node: HTMLElement | null, block: ScrollLogicalPosition) =>
    node?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block });

  // A new post starts at the top of the card; an answer brings the result into view.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) return;
    if (card.current && card.current.getBoundingClientRect().top < 0) scrollTo(card.current, "start");
  }, [index]);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    scrollTo(answers.current, "start");
  }, [answerCount]);

  return (
    <section ref={card} aria-labelledby="look-again-title" className="flex scroll-mt-4 flex-col gap-5 rounded-[3px] border border-rule bg-label p-5 sm:p-6">
      <div className="flex items-baseline gap-3 border-b border-rule pb-3">
        <h2 id="look-again-title" className="flex-1 text-title font-extrabold tracking-[-0.01em]">
          Look Again
        </h2>
        {inProgress && (
          <span aria-hidden className="text-small text-muted">
            {Math.min(index + 1, round.length)} of {round.length}
          </span>
        )}
      </div>

      {phase.kind === "finished" ? (
        <PracticeSummary round={round} picks={picks} />
      ) : (
        question && (
          <>
            {inProgress ? (
              <RoundDots round={round} picks={picks} index={index} finished={false} />
            ) : (
              <div className="flex flex-col gap-1">
                <p className="max-w-[65ch] text-muted">
                  Is each post real, edited, made by AI, or a real photo with a false story? {round.length} posts, about two minutes.
                </p>
                <details className="group">
                  <summary className="flex min-h-11 cursor-pointer list-none items-center gap-1 font-semibold text-accent [&::-webkit-details-marker]:hidden">
                    What the answers mean
                    <ChevronDown aria-hidden className="size-4 transition-transform group-open:rotate-180" />
                  </summary>
                  <dl className="grid gap-x-6 gap-y-2 pb-1 sm:grid-cols-2">
                    {practiceAnswers.map((answer) => (
                      <div key={answer}>
                        <dt className="font-semibold">{answerLabel[answer]}</dt>
                        <dd className="text-small text-muted">{answerDefinition[answer]}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              </div>
            )}

            <PracticePost key={question.id} question={question} />

            <div ref={answers} className="scroll-mt-24">
              <AnswerButtons picked={picked} answer={question.answer} />
            </div>

            {picked && (
              <>
                <PracticeFeedback question={question} picked={picked} answerCount={answerCount} live />
                <Button onClick={nextQuestion} className="self-start">
                  {isLast ? "See results" : "Next post"}
                  <ArrowRight aria-hidden className="size-[18px]" />
                </Button>
              </>
            )}
          </>
        )
      )}
    </section>
  );
}

/** One mark per question: filled for right, hollow for wrong, and a wider bar for the current one, so none of it depends on colour alone. */
function RoundDots({ round, picks, index, finished }: { round: PracticeQuestion[]; picks: PracticeAnswer[]; index: number; finished: boolean }) {
  const score = picks.filter((pick, i) => pick === round[i].answer).length;
  const label = finished
    ? `${score} of ${round.length} right`
    : `Question ${Math.min(index + 1, round.length)} of ${round.length}, ${score} right so far`;
  return (
    <div role="img" aria-label={label} className="flex items-center gap-1.5">
      {round.map((question, i) => {
        const current = !finished && i === index && i >= picks.length;
        const answered = i < picks.length;
        return (
          <span
            key={question.id}
            className={cx(
              "h-2.5 rounded-full transition-[width] duration-300",
              current ? "w-6 bg-accent" : "w-2.5",
              answered && (picks[i] === question.answer ? "bg-accent" : "border-[1.5px] border-muted"),
              !current && !answered && "bg-rule",
            )}
          />
        );
      })}
    </div>
  );
}

/** Initials standing in for an avatar. */
function Monogram({ name }: { name: string }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join("");
  return (
    <span aria-hidden className="grid size-9 shrink-0 place-items-center rounded-full bg-uv text-small font-semibold text-on-uv">
      {initials}
    </span>
  );
}

/** A practice case drawn like a post: who, when, the caption, what the photo shows, and any reply-style context. */
function PracticePost({ question }: { question: PracticeQuestion }) {
  return (
    <article className="flex flex-col gap-3 rounded-[3px] border border-rule p-4 sm:p-5">
      <header className="flex items-center gap-2.5">
        <Monogram name={question.author} />
        <span className="min-w-0">
          <span className="block truncate font-semibold">{question.author}</span>
          <span className="block truncate text-small text-muted">
            @{question.handle} · {question.posted}
          </span>
        </span>
      </header>
      <p className="max-w-[65ch]">{question.caption}</p>
      <div className="flex min-h-36 flex-col justify-center gap-2 rounded-[3px] border border-dashed border-rule-strong bg-well px-5 py-6">
        <span className="flex items-center gap-2 text-small font-semibold text-muted">
          <ImageIcon aria-hidden className="size-4 shrink-0" />
          The photo
        </span>
        <p className="max-w-[65ch] text-pretty">{question.imageDescription}</p>
      </div>
      {question.context && (
        <p className="flex items-start gap-2 text-small text-muted">
          <Reply aria-hidden className="mt-0.5 size-4 shrink-0" />
          {question.context}
        </p>
      )}
    </article>
  );
}

/**
 * The four answers, as plain words until you pick so none looks like the
 * right one. Afterwards the correct answer is marked and a wrong pick gets a
 * cross.
 */
function AnswerButtons({ picked, answer }: { picked: PracticeAnswer | null; answer: PracticeAnswer }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {practiceAnswers.map((choice) => {
        const state = picked === null ? "idle" : choice === answer ? "correct" : choice === picked ? "wrong" : "faded";
        const value = picked === null ? "" : choice === picked && choice === answer ? ", your answer, correct" : choice === picked ? ", your answer" : choice === answer ? ", correct answer" : "";
        return (
          <button
            key={choice}
            type="button"
            disabled={picked !== null}
            onClick={() => selectAnswer(choice)}
            title={picked === null ? answerDefinition[choice] : undefined}
            aria-label={`${answerLabel[choice]}${value}`}
            className={cx(
              "flex min-h-12 items-center justify-center gap-1.5 rounded-md border px-3 text-center font-semibold transition-colors duration-150",
              state === "correct" ? "border-real bg-real-wash text-real" : "border-rule-strong bg-label",
              state === "faded" && "text-muted",
              picked === null && "hover:bg-well",
            )}
          >
            {state === "correct" && <Check aria-hidden className="size-[18px]" strokeWidth={3} />}
            {state === "wrong" && <X aria-hidden className="size-[18px] text-muted" strokeWidth={3} />}
            {answerLabel[choice]}
          </button>
        );
      })}
    </div>
  );
}

/** Right or wrong, as a mark beside the headline. */
function OutcomeMark({ correct }: { correct: boolean }) {
  const Icon = correct ? Check : X;
  return (
    <span aria-hidden className={cx("grid size-9 shrink-0 place-items-center rounded-full", correct ? "bg-real text-label" : "border-[1.5px] border-muted text-muted")}>
      <Icon className="size-[18px]" strokeWidth={3} />
    </span>
  );
}

/** After answering: right or not, what to look for, then why. */
function PracticeFeedback({ question, picked, answerCount, live }: { question: PracticeQuestion; picked: PracticeAnswer; answerCount?: number; live?: boolean }) {
  const correct = picked === question.answer;
  const headline = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    // Land keyboard and screen-reader focus on the result instead of a locked answer button.
    if (live) setTimeout(() => headline.current?.focus({ preventScroll: true }), 300);
  }, [live, answerCount]);
  return (
    <div className="flex flex-col gap-3 border-t border-rule pt-4">
      <div className="flex items-center gap-3">
        <OutcomeMark correct={correct} />
        <h3 ref={headline} tabIndex={-1} className="font-semibold focus:outline-none">
          {correct ? `Yes, it's ${answerPhrase[question.answer]}.` : `Not quite. It's ${answerPhrase[question.answer]}.`}
        </h3>
      </div>
      <ul aria-label="What to look for" className="flex flex-col gap-1">
        {question.clues.map((clue) => (
          <li key={clue} className="flex gap-3 font-semibold">
            <span aria-hidden className="mt-[9px] size-1.5 shrink-0 rounded-full bg-accent" />
            {clue}
          </li>
        ))}
      </ul>
      <p className="max-w-[65ch] text-muted">{question.explanation}</p>
    </div>
  );
}

const MISS_PREVIEW = 3;

/** End of a round: the score, Play Again, what went well, and the misses to look at again. */
function PracticeSummary({ round, picks }: { round: PracticeQuestion[]; picks: PracticeAnswer[] }) {
  const router = useRouter();
  const best = useStore(app, (s) => s.bestScore);
  const isNewBest = useStore(app, (s) => s.lastRoundWasNewBest);
  const [showAll, setShowAll] = useState(false);
  const [reviewing, setReviewing] = useState<Miss | null>(null);
  const misses = missesOf(round, picks);
  const score = round.length - misses.length;
  const worst = mostMissed(misses);
  const shown = showAll || misses.length <= MISS_PREVIEW + 1 ? misses : misses.slice(0, MISS_PREVIEW);

  const reviewClues = () => {
    // On a tie, the first miss decides; never the type the player aced.
    const missed = worst ?? misses[0]?.question.answer;
    const group = (missed && groupFor(guideFocus[missed])) || clueGuide[0];
    router.push(`/learn/clues/${group.id}`);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <OutcomeMark correct={score * 2 >= round.length} />
        <div>
          <h3 className="text-title font-extrabold">
            {score} of {round.length} right
          </h3>
          {isNewBest ? (
            <p className="font-semibold text-accent">New best</p>
          ) : best === score && score > 0 ? (
            <p className="text-muted">Your best so far.</p>
          ) : (
            best !== null && (
              <p className="text-muted">
                Your best is {best} of {round.length}.
              </p>
            )
          )}
        </div>
      </div>
      <RoundDots round={round} picks={picks} index={round.length} finished />
      <p className="max-w-[65ch]">{roundSummary(round, picks)}</p>
      <Button onClick={restartPractice} icon={RotateCcw} className="self-start">
        Play again
      </Button>

      {misses.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-rule pt-4">
          <SectionTitle>Take another look</SectionTitle>
          <div className="divide-y divide-rule border-y border-rule">
            {shown.map((miss) => (
              <button
                key={miss.question.id}
                type="button"
                onClick={() => setReviewing(miss)}
                className="flex w-full items-center gap-3 py-3 text-left transition-colors hover:bg-well"
              >
                <span className="flex-1">
                  <span className="line-clamp-2">{miss.question.caption}</span>
                  <span className="block text-small text-muted">
                    You said {answerInSentence(miss.picked)}. It&apos;s {answerPhrase[miss.question.answer]}.
                  </span>
                </span>
                <ChevronRight aria-hidden className="size-[18px] shrink-0 text-muted" />
              </button>
            ))}
          </div>
          {/* Only collapse when it hides more than one row. */}
          {misses.length > MISS_PREVIEW + 1 && !showAll && (
            <Button variant="quiet" onClick={() => setShowAll(true)} className="self-start">
              Show all {misses.length}
            </Button>
          )}
          <Button variant="secondary" onClick={reviewClues} className="mt-2 self-start">
            {reviewTitle(worst)}
          </Button>
        </div>
      )}

      <Dialog open={reviewing !== null} onClose={() => setReviewing(null)} labelledBy="review-title" className="max-w-[560px]">
        {reviewing && (
          <div className="flex flex-col gap-4 p-6">
            <div className="flex items-center">
              <h3 id="review-title" className="flex-1 font-semibold">
                Take another look
              </h3>
              <Button variant="quiet" onClick={() => setReviewing(null)}>
                Done
              </Button>
            </div>
            <PracticePost question={reviewing.question} />
            <AnswerButtons picked={reviewing.picked} answer={reviewing.question.answer} />
            <PracticeFeedback question={reviewing.question} picked={reviewing.picked} />
          </div>
        )}
      </Dialog>
    </div>
  );
}

/** The clue groups, leading into the Clue Guide. */
function ClueIndex() {
  return (
    <section aria-labelledby="clue-guide-title" className="flex flex-col gap-2 lg:sticky lg:top-7">
      <SectionTitle id="clue-guide-title">Clue Guide</SectionTitle>
      <div className="divide-y divide-rule rounded-[3px] border border-rule bg-label">
        {clueGuide.map((group) => {
          const Icon = clueIcon[group.icon];
          return (
            <Link key={group.id} href={`/learn/clues/${group.id}`} className="flex items-start gap-3 px-4 py-3.5 transition-colors hover:bg-well">
              <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
              <span className="flex-1">
                <span className="block font-semibold">{group.title}</span>
                <span className="block text-small text-muted">{group.summary}</span>
              </span>
              <span className="text-small text-muted">
                <span aria-hidden>{group.clues.length}</span>
                <span className="sr-only">{group.clues.length} clues</span>
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
