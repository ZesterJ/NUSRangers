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
  const timer = setTimeout(() => controller.abort(), config.requestTimeoutMs);
  try {
    return await fn(controller.signal);
  } finally {
    clearTimeout(timer);
  }
}

const canUseBackend = () => isOnline() && getSettings().aiMode !== 'offline';

/**
 * Step 2: speech → text. Sends the recording to the backend /transcribe endpoint.
 * Returns null when offline or when transcription fails, so the screen falls back to typing.
 */
export async function transcribe(uri: string, locale: string): Promise<string | null> {
  if (!canUseBackend()) return null;
  if (getSettings().useMock) {
    await new Promise((r) => setTimeout(r, 800));
    return null; // mock has no speech model; use typing or the suggested answers
  }
  try {
    const form = new FormData();
    // React Native's FormData accepts a { uri, name, type } file descriptor.
    form.append('audio', { uri, name: 'answer.m4a', type: 'audio/m4a' } as unknown as Blob);
    form.append('locale', locale);
    const res = await withTimeout((signal) => fetch(`${base()}/transcribe`, { method: 'POST', body: form, signal }));
    if (!res.ok) return null;
    const json = (await res.json()) as { text?: string };
    return json.text?.trim() || null;
  } catch (e) {
    console.warn('[intake] transcribe failed', e);
    return null;
  }
}

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
