import type { ChatMessage } from '@/api/types';
import type { DomainPack } from '@/packs/types';

/**
 * On-device small LLM — intentionally a stub.
 *
 * To enable (needs a development build, NOT Expo Go):
 *   1. npm install llama.rn  (then add its config plugin if required)
 *   2. Download a small GGUF (e.g. Qwen2.5-0.5B-Instruct Q4_K_M, ~400MB) to the app's document directory.
 *   3. Implement isReady()/generate() below with initLlama({ model }) and context.completion({ messages }).
 *   4. Set `features.onDeviceLLM: true` in the pack.
 *   5. npx eas-cli@latest build --profile development --platform android
 *
 * The router already calls this when the pack enables it and the device is offline.
 */
export const onDeviceLLM = {
  isReady(): boolean {
    return false;
  },
  async generate(_pack: DomainPack, _locale: string, _history: ChatMessage[], _question: string): Promise<string> {
    throw new Error('On-device LLM not installed');
  },
};
