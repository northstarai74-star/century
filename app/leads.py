import time

STAGES = ["new", "contacted", "qualified", "sample_sent", "won", "lost"]
HERO_WORDS = {"jaggery": 3, "gud": 3, "soya": 3, "makhana": 3, "bulk": 4, "restaurant": 4, "cafe": 4, "hotel": 4}


def score(interest: str, source: str, phone: str) -> int:
    s = 10 + (15 if phone else 0)
    t = (interest or "").lower()
    s += sum(v * 5 for k, v in HERO_WORDS.items() if k in t)
    s += {"call": 15, "whatsapp": 10, "website": 8, "instagram": 5}.get(source, 0)
    return min(s, 100)


def create(db, user, d: dict) -> dict:
    now = time.time()
    lid = db.x("INSERT INTO leads(name,phone,source,interest,stage,score,value,owner,notes,created_at,updated_at)"
               " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (d.get("name", ""), d.get("phone", ""), d.get("source", "whatsapp"), d.get("interest", ""), "new",
                score(d.get("interest", ""), d.get("source", ""), d.get("phone", "")), d.get("value"),
                d.get("owner", "Tarun Lakhanpal"), d.get("notes", ""), now, now))
    db.audit(user, "lead.create", lid)
    db.automation("lead_capture", lid)
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


def move(db, user, lid: int, stage: str, value=None, notes="") -> dict:
    if stage not in STAGES:
        raise ValueError("bad stage")
    db.x("UPDATE leads SET stage=?, value=COALESCE(?,value), notes=CASE WHEN ?='' THEN notes ELSE ? END, updated_at=? WHERE id=?",
         (stage, value, notes, notes, time.time(), lid))
    db.audit(user, "lead.move", lid, {"stage": stage})
    if stage in ("contacted", "qualified", "sample_sent"):
        db.automation("lead_followup", lid)
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))
