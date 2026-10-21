import os
import tempfile
import time

os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["BOOTSTRAP_USERS"] = "Rahul:md:t-md,Tarun:marketing:t-mk,QA:qa:t-qa,View:viewer:t-vw"

from fastapi.testclient import TestClient  # noqa: E402

from app import compliance, inbox  # noqa: E402
from app.main import app  # noqa: E402

H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
GOOD = "Cheeni ki jagah gud. No added colour. No chemicals. Save this for chai time. #Century #PureHomeFood #CenturySince1980"


def test_banned_and_cta():
    r = compliance.check_post("This sugar-free organic gud cures all. Buy now! Used by Saffola")
    assert len(r["errors"]) >= 5


def test_clean_caption_passes():
    assert compliance.check_post(GOOD)["errors"] == []


def test_paneer_footnote_and_makhana():
    assert compliance.check_post("35% more protein than paneer #Century")["errors"]
    assert compliance.check_post("35% more protein than paneer* #Century")["errors"] == []
    assert compliance.check_post("Makhana is high protein")["errors"]


def test_post_flow_roles():
    with TestClient(app) as c:
        p = c.post("/api/posts", json={"caption": GOOD, "hero": "jaggery"}, headers=H("t-mk")).json()
        assert p["status"] == "approved"
        bad = c.post("/api/posts", json={"caption": "Sugar-free gud"}, headers=H("t-mk")).json()
        assert bad["status"] == "draft"
        brand = c.post("/api/posts", json={"caption": GOOD, "bucket": "brand"}, headers=H("t-mk")).json()
        assert brand["status"] == "needs_md"
        assert c.post(f"/api/posts/{brand['id']}/review", json={"decision": "approve"}, headers=H("t-mk")).status_code == 400
        assert c.post(f"/api/posts/{brand['id']}/review", json={"decision": "approve"}, headers=H("t-md")).json()["status"] == "approved"
        paid = c.post("/api/posts", json={"caption": GOOD, "hero": "poha", "is_paid": True}, headers=H("t-mk")).json()
        assert paid["status"] == "draft"  # paid spend is hero-only
        assert c.post("/api/posts", json={"caption": GOOD}, headers=H("t-vw")).status_code == 403
        assert c.get("/api/posts").status_code == 401
        s = c.post(f"/api/posts/{p['id']}/schedule", json={"when": time.time() + 3600}, headers=H("t-mk"))
        assert s.json()["status"] == "scheduled"


def test_inbox_rules():
    assert inbox.classify("is this jaggery good for diabetics?")[0] == "diabetic"
    assert inbox.classify("found insect in pack")[1] == "qa"
    assert inbox.classify("my lawyer will send a notice")[1] == "md"
    with TestClient(app) as c:
        m = c.post("/api/messages", json={"channel": "instagram", "sender": "a", "body": "Where can I buy?"}, headers=H("t-mk")).json()
        assert m["status"] == "auto_replied" and "Launching very soon" in m["reply"]
        m = c.post("/api/messages", json={"channel": "whatsapp", "sender": "b", "body": "bad quality, stale makhana"}, headers=H("t-mk")).json()
        assert m["status"] == "escalated_qa"


def test_leads_and_roi():
    with TestClient(app) as c:
        l = c.post("/api/leads", json={"name": "Cafe X", "phone": "9", "source": "call", "interest": "bulk jaggery"}, headers=H("t-mk")).json()
        c.post(f"/api/leads/{l['id']}/move", json={"stage": "won", "value": 5000}, headers=H("t-mk"))
        r = c.get("/api/roi", headers=H("t-vw")).json()
        assert r["won"] == 1 and r["won_value_inr"] == 5000 and r["hours_saved"] > 0
