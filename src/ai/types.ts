import type { ChatMessage } from '@/api/types';
import type { DomainPack } from '@/packs/types';

/** Where an answer came from — shown as a badge on every bot message. */
export type AiSource = 'offline' | 'cache' | 'on-device' | 'cloud' | 'fallback';

export type AskInput = {
  pack: DomainPack;
  locale: string;
  question: string;
  history: ChatMessage[];
};

export type AiReply = {
  text: string;
  source: AiSource;
  /** True when we could not answer well and the question was queued / can be sent via SMS. */
  suggestSms?: boolean;
  /** 0 = perfect match … 1 = no match (Fuse.js score). Only for offline answers. */
  score?: number;
};
