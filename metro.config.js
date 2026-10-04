// https://docs.expo.dev/versions/latest/sdk/sqlite/#web-setup
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// expo-sqlite on web runs SQLite as WebAssembly in a worker.
config.resolver.assetExts.push('wasm');

// The worker needs SharedArrayBuffer, which browsers only enable with these headers.
config.server.enhanceMiddleware = (middleware) => (req, res, next) => {
  res.setHeader('Cross-Origin-Embedder-Policy', 'credentialless');
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  middleware(req, res, next);
};

module.exports = config;
