import asyncio
import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from . import config, inbox, leads, roi, workflow
from .db import DB
from .integrations import site_health
from .integrations.meta import Meta
from .integrations.sarvam import Sarvam
from .integrations.whatsapp import WhatsApp

cfg = config.load()
db = DB(cfg.db_path)
meta, sarvam, wa = Meta(cfg), Sarvam(cfg), WhatsApp(cfg)
DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
STATIC = Path(__file__).parent / "static"


def bootstrap_users():
    """BOOTSTRAP_USERS='Rahul Arora:md:tok1,Tarun Lakhanpal:marketing:tok2,QA Lead:qa:tok3' (tokens from your secret store)."""
    for item in filter(None, os.environ.get("BOOTSTRAP_USERS", "").split(",")):
        name, role, token = [p.strip() for p in item.split(":", 2)]
        if role not in workflow.ROLES:
            raise SystemExit(f"bad role {role}")
        if not db.one("SELECT 1 FROM users WHERE token=?", (token,)):
            db.x("INSERT INTO users(name,role,token) VALUES(?,?,?)", (name, role, token))


bootstrap_users()


def user_dep(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    if token:
        for u in db.q("SELECT * FROM users"):
            if hmac.compare_digest(u["token"], token):
                return u
    if DEV_MODE:
        return {"name": "dev", "role": "md"}
    raise HTTPException(401, "invalid or missing token")


def need(*roles):
    def dep(u=Depends(user_dep)):
        if u["role"] not in roles:
            raise HTTPException(403, f"role '{u['role']}' not allowed")
        return u
    return dep


async def background():
    while True:
        try:
            now = time.time()
            for p in db.q("SELECT * FROM posts WHERE status='scheduled' AND scheduled_for<=?", (now,)):
                publish(p)
            last = db.one("SELECT MAX(ts) t FROM site_checks")["t"] or 0
            if now - last > 900:
                run_site_check()
        except Exception as e:  # keep the loop alive
            db.audit("system", "background.error", "", {"error": str(e)[:200]})
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_):
    t = asyncio.create_task(background())
    yield
    t.cancel()


app = FastAPI(title="Century Marketing Command Centre", lifespan=lifespan)


def publish(p: dict):
    if p["status"] != "scheduled":
        return
    res = meta.publish(p)  # media_url comes from the media library once uploads are wired
    status = "published" if not res.get("dry_run") else "published_dry_run"
    db.x("UPDATE posts SET status=?, published_at=?, platform_ids=? WHERE id=?",
         (status, time.time(), str(res), p["id"]))
    db.automation("post", p["id"])
    db.audit("system", "post.publish", p["id"], {"result": status})


def run_site_check():
    out = site_health.check(cfg.site_url)
    for r in out:
        db.x("INSERT INTO site_checks(ts,url,ok,status,ms,ssl_days,error) VALUES(?,?,?,?,?,?,?)",
             (time.time(), r["url"], r["ok"], r["status"], r["ms"], r["ssl_days"], r["error"]))
    db.automation("site_check")
    return out


# ---------- models ----------
class PostIn(BaseModel):
    title: str = ""
    bucket: str = "product"
    hero: str = ""
    format: str = "reel"
    caption: str
    cta: str = ""
    hashtags: str = "#Century #PureHomeFood #CenturySince1980"
    is_paid: bool = False
    is_creator: bool = False


class ReviewIn(BaseModel):
    decision: str
    note: str = ""


class ScheduleIn(BaseModel):
    when: float


class MetricsIn(BaseModel):
    reach: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    saves: int = 0
    shares: int = 0
    profile_visits: int = 0
    link_clicks: int = 0
    wa_clicks: int = 0
    followers: int = 0


class LeadIn(BaseModel):
    name: str = ""
    phone: str = ""
    source: str = "whatsapp"
    interest: str = ""
    value: float | None = None
    notes: str = ""


class MoveIn(BaseModel):
    stage: str
    value: float | None = None
    notes: str = ""


class MessageIn(BaseModel):
    channel: str
    sender: str
    body: str
    post_id: int | None = None


def wrap(fn, *a):
    try:
        return fn(*a)
    except workflow.WorkflowError as e:
        raise HTTPException(400, str(e))


# ---------- posts ----------
@app.post("/api/posts")
def post_create(d: PostIn, u=Depends(need("md", "marketing"))):
    return wrap(workflow.create_post, db, cfg, u, d.model_dump())


@app.get("/api/posts")
def post_list(status: str | None = None, _=Depends(user_dep)):
    return db.q("SELECT * FROM posts WHERE (?1 IS NULL OR status=?1) ORDER BY id DESC", (status,))


@app.post("/api/posts/{pid}/resubmit")
def post_resubmit(pid: int, u=Depends(need("md", "marketing"))):
    return wrap(workflow.submit, db, cfg, u, pid)


@app.post("/api/posts/{pid}/review")
def post_review(pid: int, d: ReviewIn, u=Depends(need("md", "qa", "marketing"))):
    out = wrap(workflow.review, db, cfg, u, pid, d.decision, d.note)
    return {**out, "warning": workflow.md_review_warning()}


@app.post("/api/posts/{pid}/schedule")
def post_schedule(pid: int, d: ScheduleIn, u=Depends(need("md", "marketing"))):
    return wrap(workflow.schedule, db, cfg, u, pid, d.when)


@app.post("/api/posts/{pid}/metrics")
def post_metrics(pid: int, d: MetricsIn, u=Depends(need("md", "marketing"))):
    db.x("INSERT INTO post_metrics(post_id,ts,reach,views,likes,comments,saves,shares,profile_visits,link_clicks,wa_clicks,followers)"
         " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
         (pid, time.time(), d.reach, d.views, d.likes, d.comments, d.saves, d.shares, d.profile_visits,
          d.link_clicks, d.wa_clicks, d.followers))
    return {"ok": True}


@app.get("/api/growth")
def growth(_=Depends(user_dep)):
    rows = db.q("""SELECT p.id, p.title, p.hero, p.format, m.reach, m.views, m.saves, m.shares, m.link_clicks, m.wa_clicks,
                   m.followers, ROUND(1000.0*(m.saves+m.shares)/NULLIF(m.reach,0),1) AS saves_shares_per_1k
                   FROM posts p JOIN post_metrics m ON m.post_id=p.id
                   WHERE m.id=(SELECT MAX(id) FROM post_metrics WHERE post_id=p.id)""")
    ranked = sorted(rows, key=lambda r: r["saves_shares_per_1k"] or 0, reverse=True)
    n = len(ranked)
    return {"posts": ranked, "top3": ranked[:3], "bottom3": ranked[-3:] if n > 3 else [],
            "boost_candidates": ranked[:max(1, n // 5)] if n else [],
            "followers": db.one("SELECT followers FROM post_metrics ORDER BY id DESC LIMIT 1") or {}}


# ---------- inbox ----------
@app.post("/api/messages")
def msg_ingest(d: MessageIn, _=Depends(need("md", "marketing"))):
    return inbox.ingest(db, cfg, d.channel, d.sender, d.body, post_id=d.post_id)


@app.get("/api/messages")
def msg_list(_=Depends(user_dep)):
    return {"messages": db.q("SELECT * FROM messages ORDER BY id DESC LIMIT 200"), "sla_breaches": inbox.sla_breaches(db)}


@app.post("/api/messages/{mid}/resolve")
def msg_resolve(mid: int, reply: str = "", u=Depends(need("md", "marketing", "qa"))):
    db.x("UPDATE messages SET status='resolved', reply=COALESCE(NULLIF(?,''),reply), replied_at=? WHERE id=?",
         (reply, time.time(), mid))
    db.audit(u["name"], "message.resolve", mid)
    return {"ok": True}


# ---------- WhatsApp webhook (Meta) ----------
@app.get("/webhooks/whatsapp")
def wa_verify(request: Request):
    q = request.query_params
    if q.get("hub.verify_token") == cfg.meta_verify_token:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403)


@app.post("/webhooks/whatsapp")
async def wa_in(request: Request):
    for m in wa.parse_webhook(await request.json()):
        row = inbox.ingest(db, cfg, "whatsapp", m["sender"], m["body"], ext_id=m["ext_id"])
        if row["status"] == "auto_replied" and row["reply"]:
            wa.send_text(m["sender"], row["reply"])
        if not db.one("SELECT 1 FROM leads WHERE phone=?", (m["sender"],)):
            leads.create(db, "system", {"name": m["name"], "phone": m["sender"], "source": "whatsapp", "interest": m["body"]})
    return {"ok": True}


# ---------- voice (telephony provider posts audio here) ----------
@app.post("/api/voice/turn")
async def voice_turn(request: Request, caller: str = "", language_code: str = "unknown", _=Depends(need("md", "marketing"))):
    audio = await request.body()
    stt = sarvam.transcribe(audio, language_code=language_code)
    text = stt.get("transcript", "")
    en = sarvam.translate(text, target="en-IN") if text else ""
    cat, esc = inbox.classify(en or text)
    answer = None if esc else inbox.draft_reply(cfg, cat)
    if esc:
        answer = "I'm connecting you to our team. You can also reach us on 1800 296 7999."
    elif not answer:
        answer = "Thank you for calling Century. Our team will call you back shortly. You can also WhatsApp us."
    speak_lang = stt.get("language_code") if stt.get("language_code") not in (None, "unknown") else "hi-IN"
    audio_out = sarvam.speak(answer if speak_lang.startswith("en") else sarvam.translate(answer, "en-IN", speak_lang), speak_lang)
    lid = None
    if caller:
        row = db.one("SELECT id FROM leads WHERE phone=?", (caller,))
        lid = row["id"] if row else leads.create(db, "system", {"phone": caller, "source": "call", "interest": en or text})["id"]
    db.x("INSERT INTO calls(caller,ts,transcript,answer,language,duration,lead_id,handled_by) VALUES(?,?,?,?,?,?,?,?)",
         (caller, time.time(), text, answer, speak_lang, 0, lid, "escalated" if esc else "ai"))
    db.automation("call")
    return {"transcript": text, "category": cat, "answer": answer, "escalate_to": esc,
            "audio_b64": __import__("base64").b64encode(audio_out).decode() if audio_out else None,
            "dry_run": not sarvam.live}


@app.get("/api/calls")
def calls(_=Depends(user_dep)):
    return db.q("SELECT * FROM calls ORDER BY id DESC LIMIT 100")


# ---------- leads ----------
@app.post("/api/leads")
def lead_new(d: LeadIn, u=Depends(need("md", "marketing"))):
    return leads.create(db, u["name"], d.model_dump())


@app.get("/api/leads")
def lead_list(_=Depends(user_dep)):
    return {"leads": db.q("SELECT * FROM leads ORDER BY score DESC, id DESC"), "stages": leads.STAGES}


@app.post("/api/leads/{lid}/move")
def lead_move(lid: int, d: MoveIn, u=Depends(need("md", "marketing"))):
    try:
        return leads.move(db, u["name"], lid, d.stage, d.value, d.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------- site health / roi / misc ----------
@app.post("/api/site/check")
def site_run(_=Depends(need("md", "marketing"))):
    return run_site_check()


@app.get("/api/site")
def site_status(_=Depends(user_dep)):
    rows = db.q("SELECT * FROM site_checks ORDER BY id DESC LIMIT 100")
    up = [r["ok"] for r in rows]
    return {"latest": rows[:3], "history": rows, "uptime_pct": round(100 * sum(up) / len(up), 1) if up else None}


@app.get("/api/roi")
def roi_get(days: int = 30, _=Depends(user_dep)):
    return roi.summary(db, cfg, days)


@app.get("/api/overview")
def overview(_=Depends(user_dep)):
    counts = {r["status"]: r["n"] for r in db.q("SELECT status, COUNT(*) n FROM posts GROUP BY status")}
    return {"posts_by_status": counts, "sales_open": cfg.sales_open,
            "sla_breaches": len(inbox.sla_breaches(db)),
            "open_leads": db.one("SELECT COUNT(*) n FROM leads WHERE stage NOT IN ('won','lost')")["n"],
            "live": {"meta": meta.live, "sarvam": sarvam.live, "whatsapp": wa.live},
            "roi": roi.summary(db, cfg), "md_note": workflow.md_review_warning()}


@app.get("/api/audit")
def audit(_=Depends(need("md", "qa", "marketing"))):
    return db.q("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")


@app.get("/api/me")
def me(u=Depends(user_dep)):
    return {"name": u["name"], "role": u["role"]}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
