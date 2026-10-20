import type { VerdictType } from "../models/verdict";

/**
 * The four answers in Look Again. Practice-only: the detector still has
 * three verdicts, but the most common misleading Bluesky post is a real photo
 * with a false story, and players should learn to name it.
 */
export type PracticeAnswer = "real" | "edited" | "ai" | "misleading";

export const practiceAnswers: PracticeAnswer[] = ["real", "edited", "ai", "misleading"];

export const answerLabel: Record<PracticeAnswer, string> = {
  real: "Real",
  edited: "Edited",
  ai: "AI",
  misleading: "False story",
};

/** Reads after "It's …": "It's a real photo." */
export const answerPhrase: Record<PracticeAnswer, string> = {
  real: "a real photo",
  edited: "an edited photo",
  ai: "made by AI",
  misleading: "a real photo with a false story",
};

/** Mid-sentence form: "You said AI", "You said edited". */
export const answerInSentence = (answer: PracticeAnswer) =>
  answer === "ai" ? answerLabel.ai : answerLabel[answer].toLowerCase();

export const answerDefinition: Record<PracticeAnswer, string> = {
  real: "The photo is what the post says it is.",
  edited: "A real photo with part of it changed.",
  ai: "The whole image was generated.",
  misleading: "A real, unedited photo with the wrong date, place or story.",
};

const singularNoun: Record<PracticeAnswer, string> = {
  real: "real photo",
  edited: "edited photo",
  ai: "AI image",
  misleading: "false story",
};

const pluralNoun: Record<PracticeAnswer, string> = {
  real: "real photos",
  edited: "edited photos",
  ai: "AI images",
  misleading: "false stories",
};

/** Which clue group helps with this answer. */
export const guideFocus: Record<PracticeAnswer, VerdictType> = {
  real: "real",
  misleading: "real",
  edited: "tampered",
  ai: "ai",
};

/** One Look Again case, shaped like a Bluesky post. */
export interface PracticeQuestion {
  id: string;
  author: string;
  handle: string;
  /** Relative time as Bluesky shows it, e.g. "2h". */
  posted: string;
  caption: string;
  /** What the photo shows, for text-only play. */
  imageDescription: string;
  /** Facts a photo can't show (replies, other coverage), drawn under the post like a reply. */
  context?: string;
  answer: PracticeAnswer;
  /** Why that answer is right, shown after the user picks. */
  explanation: string;
  clues: string[];
}

export const ROUND_LENGTH = 8;

function shuffled<T>(items: T[]) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

/**
 * An even mix of answers (two of each for a round of eight), preferring
 * cases not in `avoiding`, topped up from the rest when a type runs short.
 */
export function drawRound(bank: PracticeQuestion[], avoiding: Set<string>) {
  const perAnswer = ROUND_LENGTH / practiceAnswers.length;
  const picked: PracticeQuestion[] = [];
  for (const answer of practiceAnswers) {
    const pool = bank.filter((q) => q.answer === answer);
    const fresh = shuffled(pool.filter((q) => !avoiding.has(q.id)));
    const stale = shuffled(pool.filter((q) => avoiding.has(q.id)));
    picked.push(...[...fresh, ...stale].slice(0, perAnswer));
  }
  if (picked.length < ROUND_LENGTH) {
    const ids = new Set(picked.map((q) => q.id));
    picked.push(...shuffled(bank.filter((q) => !ids.has(q.id))).slice(0, ROUND_LENGTH - picked.length));
  }
  return shuffled(picked);
}

export interface Miss {
  question: PracticeQuestion;
  picked: PracticeAnswer;
}

export const missesOf = (round: PracticeQuestion[], picks: PracticeAnswer[]): Miss[] =>
  picks
    .map((picked, index) => ({ question: round[index], picked }))
    .filter(({ question, picked }) => question.answer !== picked);

/** The answer missed most, or null when nothing was missed or misses are tied. */
export function mostMissed(misses: Miss[]): PracticeAnswer | null {
  const counts = new Map<PracticeAnswer, number>();
  for (const { question } of misses) counts.set(question.answer, (counts.get(question.answer) ?? 0) + 1);
  const top = Math.max(0, ...counts.values());
  const leaders = [...counts].filter(([, count]) => count === top);
  return leaders.length === 1 ? leaders[0][0] : null;
}

/** The answer type the user got all of, to lead the summary with something they did well. */
export function strongest(round: PracticeQuestion[], picks: PracticeAnswer[]): PracticeAnswer | null {
  const answered = picks.map((picked, index) => ({ question: round[index], picked }));
  return (
    practiceAnswers.find((answer) => {
      const cases = answered.filter(({ question }) => question.answer === answer);
      return cases.length > 0 && cases.every(({ question, picked }) => question.answer === picked);
    }) ?? null
  );
}

export function roundSummary(round: PracticeQuestion[], picks: PracticeAnswer[]) {
  const misses = missesOf(round, picks);
  if (misses.length === 0) return "Every one right.";
  const parts: string[] = [];
  const best = strongest(round, picks);
  if (best) parts.push(`You caught every ${singularNoun[best]}.`);
  const worst = mostMissed(misses);
  parts.push(worst ? `Most misses were ${pluralNoun[worst]}.` : "Your misses were spread across answer types.");
  return parts.join(" ");
}

export function reviewTitle(worst: PracticeAnswer | null) {
  switch (worst) {
    case "ai":
      return "Clues for AI images";
    case "edited":
      return "Clues for edited photos";
    case "real":
    case "misleading":
      return "How to check a source";
    default:
      return "Clues for what you missed";
  }
}
