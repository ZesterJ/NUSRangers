import os

# Tests never call the real API.
os.environ.setdefault("LLM_PROVIDER", "echo")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
