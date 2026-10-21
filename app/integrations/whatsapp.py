"""WhatsApp Cloud API (Meta). Sarvam handles language only; WhatsApp transport is Meta's."""
import httpx


class WhatsApp:
    def __init__(self, cfg):
        self.cfg = cfg

    @property
    def live(self):
        return bool(self.cfg.wa_token and self.cfg.wa_phone_id)

    def send_text(self, to: str, text: str) -> dict:
        if not self.live:
            return {"dry_run": True}
        r = httpx.post(f"https://graph.facebook.com/v21.0/{self.cfg.wa_phone_id}/messages", timeout=30,
                       headers={"Authorization": f"Bearer {self.cfg.wa_token}"},
                       json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})
        r.raise_for_status()
        return r.json()

    @staticmethod
    def parse_webhook(payload: dict) -> list[dict]:
        out = []
        for e in payload.get("entry", []):
            for ch in e.get("changes", []):
                v = ch.get("value", {})
                names = {c["wa_id"]: c.get("profile", {}).get("name", "") for c in v.get("contacts", [])}
                for m in v.get("messages", []):
                    body = (m.get("text") or {}).get("body", "") if m.get("type") == "text" else f"[{m.get('type')}]"
                    out.append({"ext_id": m["id"], "sender": m["from"], "name": names.get(m["from"], ""), "body": body})
        return out
