import { api } from '@/api/client';
import type { ChatMessage } from '@/api/types';
import type { DomainPack } from '@/packs/types';

/** Keep payloads small for slow links: only the last few turns are sent. */
const MAX_HISTORY = 8;

export async function askCloud(pack: DomainPack, locale: string, history: ChatMessage[], question: string) {
  const res = await api.chat({
    packId: pack.id,
    locale,
    systemPrompt: pack.systemPrompt,
    messages: [...history.slice(-MAX_HISTORY), { role: 'user', content: question }],
  });
  return res.reply;
}
