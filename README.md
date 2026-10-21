# Century® Marketing Command Centre
Team-shared dashboard + automation for Century's digital marketing (see `CLAUDE.md` for the project memory and
`docs/brand/` for the brand sources of truth).

**Run locally:** `pip install -r requirements.txt && DEV_MODE=true uvicorn app.main:app --reload`
**Cloud/team:** set `BOOTSTRAP_USERS="Rahul Arora:md:<token>,Tarun Lakhanpal:marketing:<token>,<QA name>:qa:<token>"`
from your secret manager, plus API keys from `.env.example`; mount a volume at `/data`. Do NOT set `DEV_MODE` in the cloud.
**Webhooks:** WhatsApp → `/webhooks/whatsapp`; telephony audio → `POST /api/voice/turn`.
**Tests:** `pytest -q`
