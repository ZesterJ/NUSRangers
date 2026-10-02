import { config } from '@/config';
import { getSettings } from '@/store/settings';

import { mockApi } from './mock';
import type { AnalyzeRequest, AnalyzeResponse, ChatRequest, ChatResponse, PredictRequest, PredictResponse } from './types';

async function post<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.requestTimeoutMs);
  try {
    const res = await fetch(`${getSettings().apiUrl.replace(/\/$/, '')}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`${path} failed: HTTP ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

const httpApi = {
  predict: (req: PredictRequest) => post<PredictResponse>('/predict', req),
  chat: (req: ChatRequest) => post<ChatResponse>('/chat', req),
  analyze: (req: AnalyzeRequest) => post<AnalyzeResponse>('/analyze', req),
};

/** Picks the mock or the real backend at call time, so the Settings toggle applies immediately. */
export const api = {
  predict: (req: PredictRequest) => (getSettings().useMock ? mockApi : httpApi).predict(req),
  chat: (req: ChatRequest) => (getSettings().useMock ? mockApi : httpApi).chat(req),
  analyze: (req: AnalyzeRequest) => (getSettings().useMock ? mockApi : httpApi).analyze(req),
};
