"""Meta Graph API: publish to IG/FB and pull comments/metrics. Dry-run without tokens."""
import httpx

GRAPH = "https://graph.facebook.com/v21.0"


class Meta:
    def __init__(self, cfg):
        self.cfg = cfg

    @property
    def live(self):
        return bool(self.cfg.meta_token and self.cfg.meta_ig_user)

    def publish(self, post: dict, media_url: str | None = None) -> dict:
        text = f"{post['caption']}\n\n{post.get('hashtags') or ''}".strip()
        if not self.live or not media_url:
            return {"dry_run": True, "caption": text}
        t = self.cfg.meta_token
        is_reel = post.get("format") == "reel"
        body = {"caption": text, "access_token": t}
        body.update({"media_type": "REELS", "video_url": media_url} if is_reel else {"image_url": media_url})
        c = httpx.post(f"{GRAPH}/{self.cfg.meta_ig_user}/media", data=body, timeout=60)
        c.raise_for_status()
        p = httpx.post(f"{GRAPH}/{self.cfg.meta_ig_user}/media_publish",
                       data={"creation_id": c.json()["id"], "access_token": t}, timeout=60)
        p.raise_for_status()
        return {"ig_media_id": p.json()["id"]}

    def comments(self, media_id: str) -> list[dict]:
        if not self.live:
            return []
        r = httpx.get(f"{GRAPH}/{media_id}/comments", timeout=30,
                      params={"fields": "id,text,username,timestamp", "access_token": self.cfg.meta_token})
        r.raise_for_status()
        return r.json().get("data", [])

    def reply_comment(self, comment_id: str, text: str) -> dict:
        if not self.live:
            return {"dry_run": True}
        r = httpx.post(f"{GRAPH}/{comment_id}/replies", data={"message": text, "access_token": self.cfg.meta_token}, timeout=30)
        r.raise_for_status()
        return r.json()

    def insights(self, media_id: str) -> dict:
        if not self.live:
            return {}
        r = httpx.get(f"{GRAPH}/{media_id}/insights", timeout=30, params={
            "metric": "reach,saved,shares,likes,comments,views", "access_token": self.cfg.meta_token})
        r.raise_for_status()
        return {m["name"]: m["values"][0]["value"] for m in r.json().get("data", [])}
