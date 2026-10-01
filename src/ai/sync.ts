import { create } from 'zustand';

import { api } from '@/api/client';
import type { ChatMessage } from '@/api/types';
import { addMessage, getReportImage, listOutbox, removeOutbox, setReportResult } from '@/db';
import { getPack } from '@/packs';
import type { FormValues } from '@/packs/types';
import { isOnline } from '@/store/connectivity';
import { getSettings } from '@/store/settings';

import { askCloud } from './strategies/cloudLLM';

export type QueuedChat = { packId: string; locale: string; question: string; history: ChatMessage[] };
export type QueuedReport = { packId: string; locale: string; fields: FormValues };

/** Bumped after every sync so screens know to reload from SQLite. */
export const useSyncStore = create<{ version: number; pending: number; syncing: boolean }>(() => ({
  version: 0,
  pending: 0,
  syncing: false,
}));

export async function refreshPending() {
  const items = await listOutbox();
  useSyncStore.setState({ pending: items.length });
}

let running = false;

/** Retry everything that was queued while offline. Safe to call often. */
export async function flushOutbox() {
  if (running || !isOnline() || getSettings().aiMode === 'offline') return;
  running = true;
  useSyncStore.setState({ syncing: true });
  try {
    for (const item of await listOutbox()) {
      try {
        if (item.kind === 'chat') {
          const q = JSON.parse(item.payload) as QueuedChat;
          const reply = await askCloud(getPack(q.packId), q.locale, q.history, q.question);
          await addMessage(q.packId, { role: 'assistant', text: `↪ "${q.question}"\n\n${reply}`, source: 'cloud' });
        } else {
          const r = JSON.parse(item.payload) as QueuedReport;
          const result = await api.analyze({
            packId: r.packId,
            locale: r.locale,
            fields: r.fields,
            imageBase64: await getReportImage(item.refId),
          });
          await setReportResult(item.refId, result, 'cloud');
        }
        await removeOutbox(item.id);
      } catch (e) {
        console.warn('[sync] item failed, will retry', item.id, e);
      }
    }
  } finally {
    running = false;
    await refreshPending();
    useSyncStore.setState((s) => ({ syncing: false, version: s.version + 1 }));
  }
}
