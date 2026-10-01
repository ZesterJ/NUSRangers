/** Build-time defaults from .env (EXPO_PUBLIC_* is inlined by Expo). Overridable in Settings. */
export const config = {
  apiUrl: process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000',
  useMock: (process.env.EXPO_PUBLIC_USE_MOCK ?? '1') === '1',
  defaultPack: process.env.EXPO_PUBLIC_PACK ?? 'agri',
  // Longer than the backend's own model timeout (LLM_TIMEOUT_SECONDS=25) so its 503 reaches us first.
  requestTimeoutMs: 30000,
};
