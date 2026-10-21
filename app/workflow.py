"""Approval workflow. Statuses: draft -> needs_qa | needs_md | approved -> scheduled -> published | rejected."""
import datetime as dt
import json
import time

from . import compliance

ROLES = ("md", "marketing", "qa", "viewer")


class WorkflowError(Exception):
    pass


def is_tuesday(ts: float) -> bool:
    return dt.datetime.fromtimestamp(ts).weekday() == 1


def evaluate(db, cfg, post: dict) -> dict:
    res = compliance.check_post(
        post["caption"] or "", hashtags=post.get("hashtags") or "", cta=post.get("cta") or "",
        hero=post.get("hero") or "", bucket=post.get("bucket") or "", fmt=post.get("format") or "",
        is_creator=bool(post.get("is_creator")), sales_open=cfg.sales_open)
    # MD-only categories regardless of text
    if post.get("is_paid") or post.get("is_creator"):
        res["needs_md"] = True
        if post.get("is_paid") and (post.get("hero") or "").lower() not in ("jaggery", "soya", "makhana"):
            res["errors"].append("Paid spend is for hero products only (Jaggery, Soya, Makhana)")
    return res


def create_post(db, cfg, user, data: dict) -> dict:
    now = time.time()
    pid = db.x(
        "INSERT INTO posts(title,bucket,hero,format,caption,cta,hashtags,flags,status,is_paid,is_creator,created_by,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (data.get("title", ""), data.get("bucket", "product"), data.get("hero", ""), data.get("format", "reel"),
         data.get("caption", ""), data.get("cta", ""), data.get("hashtags", ""), "{}", "draft",
         int(bool(data.get("is_paid"))), int(bool(data.get("is_creator"))), user["name"], now))
    db.audit(user["name"], "post.create", pid)
    return submit(db, cfg, user, pid)


def submit(db, cfg, user, pid: int) -> dict:
    post = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not post:
        raise WorkflowError("post not found")
    res = evaluate(db, cfg, post)
    if res["errors"] and not res["needs_qa"]:
        status = "draft"
    elif res["needs_qa"]:
        status = "needs_qa"
    elif res["needs_md"]:
        status = "needs_md"
    else:
        status = "approved"  # product post within approved briefs: Tarun alone, claims check passed
    db.x("UPDATE posts SET status=?, flags=? WHERE id=?", (status, json.dumps(res), pid))
    db.audit(user["name"], "post.submit", pid, {"status": status, "errors": res["errors"]})
    return {**db.one("SELECT * FROM posts WHERE id=?", (pid,)), "check": res}


def review(db, cfg, user, pid: int, decision: str, note: str = "") -> dict:
    post = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not post:
        raise WorkflowError("post not found")
    st, role = post["status"], user["role"]
    if decision == "reject":
        if role not in ("md", "qa", "marketing"):
            raise WorkflowError("role cannot reject")
        new = "rejected"
    elif decision == "approve":
        if st == "needs_qa":
            if role not in ("qa", "md"):
                raise WorkflowError("QA sign-off required")
            res = json.loads(post["flags"] or "{}")
            blocking = [e for e in res.get("errors", []) if not e.startswith("Certification") and "Iron/mineral" not in e]
            if blocking:
                raise WorkflowError("blocking compliance errors remain: " + "; ".join(blocking))
            new = "needs_md" if res.get("needs_md") else "approved"
        elif st == "needs_md":
            if role != "md":
                raise WorkflowError("only the MD can approve this post")
            new = "approved"
        else:
            raise WorkflowError(f"nothing to approve in status '{st}'")
    else:
        raise WorkflowError("decision must be approve or reject")
    db.x("UPDATE posts SET status=?, reviewer=?, review_note=? WHERE id=?", (new, user["name"], note, pid))
    db.audit(user["name"], f"post.{decision}", pid, {"from": st, "to": new, "note": note})
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def schedule(db, cfg, user, pid: int, when: float) -> dict:
    post = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not post or post["status"] != "approved":
        raise WorkflowError("only approved posts can be scheduled")
    if when <= time.time():
        raise WorkflowError("schedule time must be in the future")
    db.x("UPDATE posts SET status='scheduled', scheduled_for=? WHERE id=?", (when, pid))
    db.audit(user["name"], "post.schedule", pid, {"when": when})
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def md_review_warning(now: float | None = None) -> str | None:
    return "Tuesday is the MD's workshop day: ask on WhatsApp only, don't schedule reviews." if is_tuesday(now or time.time()) else None
