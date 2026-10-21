# Century® Marketing Command Centre — Project Memory

Read this first. It is the persistent memory for this repo. Full brand sources are in `docs/brand/` and are the
authority; this file is the working summary.

## What we are building
A dashboard + automation system for **Century®** (owner: Dinero FoodWorks Pvt. Ltd., site: https://thecentury.in) that:
1. Drafts, approves and auto-posts content to Instagram/Facebook (Meta Graph API) — **approval-gated**.
2. Tracks every post's performance and follows comments, DMs and WhatsApp messages in one inbox.
3. Replies automatically **only from the approved reply bank**; everything else is escalated to a human.
4. Answers WhatsApp and phone calls using **Sarvam AI** (STT / TTS / translate / chat) — keys in `.env`.
5. Monitors thecentury.in site health (uptime, latency, SSL expiry, key pages).
6. Runs lead control (capture → qualify → assign → follow-up → won/lost).
7. Converts automation into **hours saved → ₹ saved**, plus lead value won, on a ROI panel.

Users: Tarun Lakhanpal (MIS Executive, Online Sales & Digital Marketing — day-to-day owner),
Rahul Arora (MD — final approver), QA team (claims sign-off).

## Team / cloud model
Shared cloud project used by the whole team. Every API call is made by a named user (bearer token) with a role:
`md` (Rahul: approves everything), `marketing` (Tarun: drafts, QA-pass product posts, replies, leads), `qa` (claims
sign-off, complaints), `viewer` (read-only dashboard). Every state change is written to `audit_log` (who/what/when).
Config via env only; deploy with the Dockerfile; DB path is configurable (mount a persistent volume).

## Source-of-truth order
Pack artwork (names/claims) → `docs/brand/Brand_Bible.md` (everything else) → `docs/brand/Meta_Digital_Brand_Handbook.md`
(41 post briefs). If the Bible changes, update it first (new version + date), then code (`app/brand_rules.py`).

## Hard rules the code enforces (see app/compliance.py, app/brand_rules.py)
- Banned words: diabetic-friendly, safe for diabetics, sugar-free, controls blood sugar, cure(s), prevent(s), treat(s),
  boosts immunity, detox, weight loss, burns fat, guilt-free, organic, "healthier than sugar", "best in India", "purest".
- No certification names (NPOP, NOP, FSSC 22000) unless QA-approved per SKU. Never "chemical-free" for pulses/besan/poha.
- Never name B2B customers (Saffola, Marico, True Elements, Chaayos…) or any competitor in public content.
- Makhana: never "high protein"; "fat-free" only for plain makhana. Soya: keep "35% more protein than paneer*" with footnote.
- Prepared-dish visuals need "Serving suggestion". Paid/gifted creator posts need ASCI label (#ad/#collab/#sponsored).
- **No "Buy/Order" CTA until `SALES_OPEN=true`** (MD sets sales date + prices). Allowed now: follow, save, share,
  visit thecentury.in, WhatsApp us.
- Hero-first: Jaggery, Soya, Makhana ≈ 70% of content and ALL paid spend.
- Every post carries #Century #PureHomeFood #CenturySince1980. Reels 9:16 1080x1920; feed 4:5 1080x1350.
- Captions ≈70% English / 30% Hindi. On-screen text < 7 words per frame.

## Decision rights (drives app/workflow.py)
- Tarun alone: product posts within approved briefs, captions, scheduling, stories, replies from the approved bank.
- QA: any claim not on the approved list; quality-complaint investigation.
- MD: brand-level posts (Handbook Section 1 / bucket `brand`), paid campaigns, influencer deals, new claims,
  PR/media, serious complaints, legal threats, health incidents. **Never schedule MD approvals on Tuesdays** (WhatsApp only).
- Status flow: `draft → needs_qa | needs_md | approved → scheduled → published` (or `rejected`).
  Nothing publishes without `approved`. Compliance failures block approval outright.

## Community SLAs
Reply to every comment/DM ≤ 4 working hours; complaints → DM ≤ 1 hour; QA gets complaint ≤ 24h; resolution ≤ 48h.
Legal/media/health-incident messages → MD immediately. Never delete honest negative comments (hide only abuse/spam).
Contact: 1800 296 7999 · century@thecentury.in.

## Calendar (phase gates)
Phase 0 trust 21 Oct–~5 Nov 2026 (no paid) · Phase 1 hero launch ~6 Nov–6 Dec (paid from Diwali 8 Nov) ·
Phase 2 full range 7 Dec–31 Jan 2027 (Lohri 13 Jan). Cadence: 4 feed posts/week + stories 5 days.
Mon Jaggery reel, Wed Soya reel, Fri Makhana reel, weekend brand/range carousel.

## Open items (blockers — do not invent values)
Sales start date · selling prices · monthly paid Meta budget · creator budget · jaggery sachet weight ·
WhatsApp Business number & IG/FB handles · QA list behind "250+ quality parameters" · font names / master logo ·
hashtag availability check. Config fields for these exist in `.env` and default to empty/false.

## Integration notes
- **Sarvam AI** (api.sarvam.ai, header `api-subscription-key`): speech-to-text, text-to-speech, translate, chat. It does NOT
  carry WhatsApp or phone traffic itself. WhatsApp transport = Meta WhatsApp Cloud API; voice calls need a telephony
  provider (Exotel/Twilio/Knowlarity) that streams audio to our `/api/voice/*` webhooks. Verify Sarvam endpoint/model
  names against current docs before going live.
- **Meta Graph API** for IG/FB publishing and comment retrieval. Without tokens everything runs in dry-run mode.
- All adapters degrade to `dry_run` when keys are missing; never fake success in the DB (status `dry_run`).
- Secrets only in `.env` (gitignored). Never commit keys; never print them.

## ROI model (app/roi.py)
hours_saved = Σ(automated action count × minutes_per_action ÷ 60); ₹ saved = hours × hourly_cost (configurable);
lead value = won leads × avg order value (configurable, blank until prices are set). Show assumptions on the dashboard.

## Dev commands
`pip install -r requirements.txt` · `uvicorn app.main:app --reload` · `pytest -q` · dashboard at `/`.
