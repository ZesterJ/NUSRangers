import { config } from '@/config';
import { isOnline } from '@/store/connectivity';
import { getSettings } from '@/store/settings';

import { extractWithRules } from './extractRules';
import { mergeExtractions } from './mergeExtraction';
import type { Extraction } from './types';

type Answers = Parameters<typeof extractWithRules>[0];

function base() {
  return getSettings().apiUrl.replace(/\/$/, '');
}

async function withTimeout<T>(fn: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.extractTimeoutMs);
  try {
    return await fn(controller.signal);
  } finally {
    clearTimeout(timer);
  }
}

const canUseBackend = () => isOnline() && getSettings().aiMode !== 'offline';

/**
 * Step 3: text → structured symptoms. Uses the trained parser (backend /extract) when reachable,
 * combined with the on-phone rules; otherwise the rules alone. Both return the same `Extraction` shape.
 */
export async function extract(answers: Answers, locale: string): Promise<Extraction> {
  const rules = extractWithRules(answers);
  if (!canUseBackend() || getSettings().useMock) return rules;
  try {
    const res = await withTimeout((signal) =>
      fetch(`${base()}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers, locale }),
        signal,
      }),
    );
    if (!res.ok) return rules;
    const model = (await res.json()) as Extraction;
    return mergeExtractions(model, rules);
  } catch (e) {
    console.warn('[intake] extract failed, using rules', e);
    return rules;
  }
}
