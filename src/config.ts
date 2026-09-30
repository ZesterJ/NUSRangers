/** Build-time defaults from .env (EXPO_PUBLIC_* is inlined by Expo). Overridable in Settings. */
export const config = {
  apiUrl: process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000',
  useMock: (process.env.EXPO_PUBLIC_USE_MOCK ?? '1') === '1',
  defaultPack: process.env.EXPO_PUBLIC_PACK ?? 'agri',
  requestTimeoutMs: 15000,
};
