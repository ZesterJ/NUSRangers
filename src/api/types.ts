/**
 * Backend contract shared with the BE teammate. Keep in sync with docs/api.md.
 */
import type { Assessment, FormValues } from '@/packs/types';

export type ChatRole = 'system' | 'user' | 'assistant';
export type ChatMessage = { role: ChatRole; content: string };

export type ChatRequest = {
  packId: string;
  locale: string;
  systemPrompt: string;
  messages: ChatMessage[];
  /** Optional extra context, e.g. the latest capture report. */
  context?: Record<string, unknown>;
};

export type ChatResponse = {
  reply: string;
  sources?: string[];
};

export type AnalyzeRequest = {
  packId: string;
  locale: string;
  fields: FormValues;
  /** JPEG, base64 without the data: prefix. Kept small (quality 0.3) for low bandwidth. */
  imageBase64?: string;
};

export type AnalyzeResponse = Assessment;

/** Store-and-forward upload of a confirmed intake record (DHIS2-shaped on the server side). */
export type SaveRecordResponse = { ok: true };

/** Initial numeric-vector contract for backend-local inference. */
export type PredictRequest = { features: number[] };
export type PredictResponse = { prediction: number | string; modelVersion: string };
