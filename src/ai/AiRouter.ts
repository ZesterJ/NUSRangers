import { cacheAnswer, getCachedAnswer } from '@/db';
import i18n from '@/i18n';
import { isOnline } from '@/store/connectivity';
import { getSettings } from '@/store/settings';

import { askCloud } from './strategies/cloudLLM';
import { matchOffline, STRONG_MATCH, WEAK_MATCH } from './strategies/offlineMatcher';
import { onDeviceLLM } from './strategies/onDeviceLLM';
import type { AiReply, AskInput } from './types';

/**
 * Hybrid "Small AI" router. Cheapest and most available strategy first:
 *   1. Offline knowledge (fuzzy match on device)     — instant, no network
 *   2. Cloud LLM via our backend                      — best quality when online
 *   3. On-device small LLM (feature-flagged)          — offline generation
 *   4. Cached cloud answer / weak offline match       — better than nothing
 *   5. Fallback: queue for later + offer SMS
 */
export async function ask({ pack, locale, question, history }: AskInput): Promise<AiReply> {
  const { aiMode } = getSettings();
  const online = isOnline() && aiMode !== 'offline';

  const offline = aiMode === 'cloud' ? null : matchOffline(pack, question, locale);
  if (offline && offline.score <= STRONG_MATCH) {
    return { text: offline.text, source: 'offline', score: offline.score };
  }

  if (online) {
    try {
      const text = await askCloud(pack, locale, history, question);
      cacheAnswer(pack.id, locale, question, text).catch(() => {});
      return { text, source: 'cloud' };
    } catch (e) {
      console.warn('[AiRouter] cloud failed, falling back', e);
    }
  }

  if (pack.features.onDeviceLLM && onDeviceLLM.isReady()) {
    try {
      const text = await onDeviceLLM.generate(pack, locale, history, question);
      return { text, source: 'on-device' };
    } catch (e) {
      console.warn('[AiRouter] on-device failed', e);
    }
  }

  const cached = await getCachedAnswer(pack.id, locale, question).catch(() => null);
  if (cached) return { text: cached, source: 'cache' };

  if (offline && offline.score <= WEAK_MATCH) {
    return { text: offline.text, source: 'offline', score: offline.score };
  }

  return {
    text: i18n.t('chat.fallback'),
    source: 'fallback',
    suggestSms: pack.features.sms,
  };
}
