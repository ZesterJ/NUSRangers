# NUSRangers backend

FastAPI service that the mobile app calls for cloud answers (`/chat`), report assessments (`/analyze`) and SMS (`/sms/webhook`).

- Setup, local run, deploy and hackathon checklist: [`../docs/BACKEND_DEPLOY.md`](../docs/BACKEND_DEPLOY.md)
- API contract: [`../docs/api.md`](../docs/api.md)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
LLM_PROVIDER=echo uvicorn app.main:app --reload --port 8000
pytest
```
