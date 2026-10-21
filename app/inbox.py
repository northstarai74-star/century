"""Unified inbox: classify, auto-reply only from the approved bank, escalate the rest, track SLA."""
import time

from . import brand_rules as R

WORK_SLA_H, COMPLAINT_SLA_H = 4, 1


def classify(text: str) -> tuple[str, str | None]:
    t = f" {text.lower()} "
    if any(a in t for a in R.ABUSE):
        return "abuse", None
    for cat, kws, esc in R.CLASSIFY:
        if any(k in t for k in kws):
            return cat, esc
    return "general", None


def draft_reply(cfg, category: str, whatsapp_number: str = "") -> str | None:
    if category == "where_buy":
        if cfg.sales_open and whatsapp_number:
            return R.REPLY_BANK["where_buy"].format(whatsapp_number=whatsapp_number)
        return R.REPLY_BANK["where_buy_pre"]
    return R.REPLY_BANK.get(category)


def ingest(db, cfg, channel, sender, body, ext_id="", post_id=None, whatsapp_number="") -> dict:
    cat, esc = classify(body)
    now = time.time()
    reply = draft_reply(cfg, cat, whatsapp_number)
    if cat == "abuse":
        status, reply = "hidden", None
    elif esc:
        status, reply = f"escalated_{esc}", reply if cat == "complaint" else None
    elif reply:
        status = "auto_replied"
    else:
        status = "needs_human"
    mid = db.x("INSERT INTO messages(channel,ext_id,sender,body,ts,post_id,category,status,reply,replied_at,auto,escalate_to)"
               " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
               (channel, ext_id, sender, body, now, post_id, cat, status, reply,
                now if status == "auto_replied" else None, int(status == "auto_replied"), esc))
    if status == "auto_replied":
        db.automation("reply", mid)
    return db.one("SELECT * FROM messages WHERE id=?", (mid,))


def sla_breaches(db, now=None) -> list[dict]:
    now = now or time.time()
    out = []
    for m in db.q("SELECT * FROM messages WHERE replied_at IS NULL AND status NOT IN ('hidden','resolved')"):
        limit = (COMPLAINT_SLA_H if m["category"] in ("complaint", "legal", "health_incident") else WORK_SLA_H) * 3600
        if now - m["ts"] > limit:
            out.append({**m, "overdue_h": round((now - m["ts"] - limit) / 3600, 1)})
    return out
