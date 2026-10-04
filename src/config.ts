/** Build-time defaults from .env (EXPO_PUBLIC_* is inlined by Expo). Overridable in Settings. */
export const config = {
  apiUrl: process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000',
  useMock: (process.env.EXPO_PUBLIC_USE_MOCK ?? '1') === '1',
  /** Demo gate for the clinic view. It keeps patients out of the clinic screens; it is not real security. */
  clinicPin: process.env.EXPO_PUBLIC_CLINIC_PIN ?? '1234',
  defaultPack: process.env.EXPO_PUBLIC_PACK ?? 'health',
  // Longer than the backend's own model timeout (LLM_TIMEOUT_SECONDS=25) so its 503 reaches us first.
  requestTimeoutMs: 30000,
  /** Intake waits this long for the backend parser before using the on-phone rules, so a dead backend never stalls the flow. */
  extractTimeoutMs: 8000,
};
