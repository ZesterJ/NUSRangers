import { getPack } from '@/packs';

import type { IntakeRecord } from '@/intake/types';

import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ChatRequest,
  ChatResponse,
  PredictRequest,
  PredictResponse,
  SaveRecordResponse,
} from './types';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Stand-in for the backend so the FE is never blocked. Replies are clearly labelled
 * so nobody mistakes them for real model output during testing.
 */
export const mockApi = {
  async predict(_req: PredictRequest): Promise<PredictResponse> {
    // API-contract fixture only; this does not simulate a trained model.
    return { prediction: '[mock prediction]', modelVersion: 'mock-v1' };
  },
  async chat(req: ChatRequest): Promise<ChatResponse> {
    await delay(900);
    const last = [...req.messages].reverse().find((m) => m.role === 'user')?.content ?? '';
    const pack = getPack(req.packId);
    return {
      reply:
        `[mock cloud · ${pack.appName}] You asked: "${last}". ` +
        'Once the backend is connected this answer will come from the LLM using the pack system prompt.',
    };
  },

  async analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
    await delay(1200);
    const pack = getPack(req.packId);
    const base = pack.offlineAssess?.(req.fields, req.locale) ?? {
      summary: 'Report received.',
      actions: ['Follow up'],
    };
    return { ...base, summary: `[mock cloud] ${base.summary}${req.imageBase64 ? ' (photo attached)' : ''}` };
  },

  async saveRecord(_rec: IntakeRecord): Promise<SaveRecordResponse> {
    await delay(500);
    return { ok: true };
  },
};
