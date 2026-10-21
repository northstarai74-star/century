import time


def summary(db, cfg, days=30) -> dict:
    since = time.time() - days * 86400
    counts = {r["kind"]: r["n"] for r in db.q(
        "SELECT kind, COUNT(*) n FROM automation_events WHERE ts>=? GROUP BY kind", (since,))}
    m = cfg.minutes
    mapping = {"post": "post", "reply": "reply", "call": "call", "lead_followup": "lead_followup",
               "lead_capture": "lead_followup", "site_check": "site_check"}
    breakdown, total_min = [], 0.0
    for kind, n in sorted(counts.items()):
        mins = n * m.get(mapping.get(kind, kind), 0)
        total_min += mins
        breakdown.append({"kind": kind, "count": n, "hours": round(mins / 60, 2)})
    hours = total_min / 60
    won = db.q("SELECT COUNT(*) n, COALESCE(SUM(value),0) v FROM leads WHERE stage='won' AND updated_at>=?", (since,))[0]
    pipeline = db.q("SELECT COUNT(*) n, COALESCE(SUM(value),0) v FROM leads WHERE stage NOT IN ('won','lost')")[0]
    total_leads = db.q("SELECT COUNT(*) n FROM leads WHERE created_at>=?", (since,))[0]["n"]
    won_value = won["v"] or (won["n"] * cfg.avg_order_value if cfg.avg_order_value else None)
    return {
        "window_days": days, "hours_saved": round(hours, 1), "money_saved_inr": round(hours * cfg.hourly_cost),
        "breakdown": breakdown, "leads": total_leads, "won": won["n"], "won_value_inr": won_value,
        "pipeline_inr": pipeline["v"], "conversion_pct": round(100 * won["n"] / total_leads, 1) if total_leads else 0,
        "assumptions": {"hourly_cost_inr": cfg.hourly_cost, "minutes_per_action": m,
                        "avg_order_value_inr": cfg.avg_order_value,
                        "note": "Lead value is blank until prices/AOV are set by the MD." if not cfg.avg_order_value else ""},
    }
