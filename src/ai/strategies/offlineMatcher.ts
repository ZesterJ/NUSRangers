import type { DomainPack } from '@/packs/types';
import { tr } from '@/packs/types';

/**
 * Tiny on-device retrieval over the pack's knowledge. Works with zero connectivity,
 * no model download, and is easy to explain: keyword overlap between the user's
 * question and each stored question variant (all locales), scored with F1.
 */

// Small multilingual stopword list — extend when adding a locale.
const STOPWORDS = new Set(
  (
    // en
    'a an the is are am be to of in on at for and or my me i you your it its this that these those ' +
    'what when where which who how why do does did should can could would will shall there their ' +
    'have has had with from about any some please tell' +
    // sw
    ' na ya wa za la kwa ni je gani nini lini wapi vipi hii huu kuhusu' +
    // es
    ' el la los las un una de del y o en por para que qué como cómo cuando cuándo donde dónde mi mis tu es este esta'
  ).split(/\s+/),
);

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 1 && !STOPWORDS.has(t));
}

/** Crude stemming: tokens match if equal or share a 4+ char prefix (leaf/leaves, plant/planting). */
function tokenMatch(a: string, b: string) {
  if (a === b) return true;
  const n = Math.min(a.length, b.length);
  return n >= 4 && a.slice(0, 4) === b.slice(0, 4);
}

function f1(query: string[], variant: string[]) {
  if (!query.length || !variant.length) return 0;
  const hitsInVariant = variant.filter((v) => query.some((q) => tokenMatch(q, v))).length;
  const hitsInQuery = query.filter((q) => variant.some((v) => tokenMatch(q, v))).length;
  const recall = hitsInVariant / variant.length;
  const precision = hitsInQuery / query.length;
  return precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
}

type Entry = { itemId: string; tokens: string[] };
const indexCache = new Map<string, Entry[]>();

function getIndex(pack: DomainPack) {
  let entries = indexCache.get(pack.id);
  if (!entries) {
    entries = pack.offlineKnowledge.flatMap((item) =>
      Object.values(item.questions).flatMap((qs) => (qs ?? []).map((q) => ({ itemId: item.id, tokens: tokenize(q) }))),
    );
    indexCache.set(pack.id, entries);
  }
  return entries;
}

/** Returns the best answer and a score where 0 = perfect match and 1 = no overlap. */
export function matchOffline(pack: DomainPack, question: string, locale: string) {
  const query = tokenize(question);
  let best: { itemId: string; sim: number } | null = null;
  for (const e of getIndex(pack)) {
    const sim = f1(query, e.tokens);
    if (!best || sim > best.sim) best = { itemId: e.itemId, sim };
  }
  if (!best || best.sim === 0) return null;
  const item = pack.offlineKnowledge.find((k) => k.id === best.itemId);
  if (!item) return null;
  return { text: tr(item.answer, locale), score: 1 - best.sim, itemId: item.id };
}

/** Score thresholds (lower is better). Tune during the hackathon with real questions. */
export const STRONG_MATCH = 0.4;
export const WEAK_MATCH = 0.6;
