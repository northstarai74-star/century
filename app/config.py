import os
from dataclasses import dataclass


def _f(name, default=""):
    return os.environ.get(name, default)


def _num(name, default):
    try:
        return float(_f(name, str(default)))
    except ValueError:
        return float(default)


@dataclass
class Settings:
    site_url: str
    db_path: str
    sales_open: bool
    avg_order_value: float | None
    sarvam_key: str
    sarvam_base: str
    meta_token: str
    meta_ig_user: str
    meta_fb_page: str
    meta_verify_token: str
    wa_token: str
    wa_phone_id: str
    hourly_cost: float
    minutes: dict


def load() -> Settings:
    aov = _f("AVG_ORDER_VALUE_INR")
    return Settings(
        site_url=_f("SITE_URL", "https://thecentury.in"),
        db_path=_f("DB_PATH", "century.db"),
        sales_open=_f("SALES_OPEN", "false").lower() == "true",
        avg_order_value=float(aov) if aov else None,
        sarvam_key=_f("SARVAM_API_KEY"),
        sarvam_base=_f("SARVAM_BASE_URL", "https://api.sarvam.ai"),
        meta_token=_f("META_ACCESS_TOKEN"),
        meta_ig_user=_f("META_IG_USER_ID"),
        meta_fb_page=_f("META_FB_PAGE_ID"),
        meta_verify_token=_f("META_VERIFY_TOKEN", "change-me"),
        wa_token=_f("WHATSAPP_TOKEN"),
        wa_phone_id=_f("WHATSAPP_PHONE_NUMBER_ID"),
        hourly_cost=_num("HOURLY_COST_INR", 300),
        minutes={
            "post": _num("MINUTES_PER_POST", 45),
            "reply": _num("MINUTES_PER_REPLY", 4),
            "call": _num("MINUTES_PER_CALL", 6),
            "lead_followup": _num("MINUTES_PER_LEAD_FOLLOWUP", 10),
            "site_check": _num("MINUTES_PER_SITE_CHECK", 5),
        },
    )
