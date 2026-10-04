import { config } from '@/config';
import { isOnline } from '@/store/connectivity';
import { getSettings } from '@/store/settings';

import { extractWithRules } from './extractRules';
import { mergeExtractions } from './mergeExtraction';
import type { CareRouting, ConfirmedIntake, Extraction } from './types';

type Answers = Parameters<typeof extractWithRules>[0];

function base() {
  return getSettings().apiUrl.replace(/\/$/, '');
}

async function withTimeout<T>(fn: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.requestTimeoutMs);
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

/**
 * Steps 6–7: confirmed visit note → proposed care services + Kilifi facility candidates, from the backend.
 * Returns null when offline, on the mock, or when the backend cannot route; the result screen then
 * uses the on-phone clinic list. The patient's name is not sent.
 */
export async function assessCare(intake: ConfirmedIntake, locale: string): Promise<CareRouting | null> {
  if (!canUseBackend() || getSettings().useMock) return null;
  const { patientName: _name, ...note } = intake;
  try {
    const res = await withTimeout((signal) =>
      fetch(`${base()}/assess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale, note }),
        signal,
      }),
    );
    if (!res.ok) return null;
    return (await res.json()) as CareRouting;
  } catch (e) {
    console.warn('[intake] assess failed, using the on-phone clinic list', e);
    return null;
  }
}
