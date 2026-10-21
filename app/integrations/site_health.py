import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

KEY_PATHS = ["/"]  # extend once site structure is known (products, contact, etc.)


def ssl_days_left(host: str, port=443) -> int | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as s, ctx.wrap_socket(s, server_hostname=host) as t:
            exp = datetime.strptime(t.getpeercert()["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        return (exp - datetime.now(timezone.utc)).days
    except Exception:
        return None


def check(site_url: str) -> list[dict]:
    host = urlparse(site_url).hostname
    days = ssl_days_left(host) if site_url.startswith("https") else None
    results = []
    for p in KEY_PATHS:
        url = site_url.rstrip("/") + p
        t0 = time.time()
        try:
            r = httpx.get(url, timeout=15, follow_redirects=True)
            results.append({"url": url, "ok": int(r.status_code < 400), "status": r.status_code,
                            "ms": round((time.time() - t0) * 1000), "ssl_days": days, "error": ""})
        except Exception as e:
            results.append({"url": url, "ok": 0, "status": 0, "ms": round((time.time() - t0) * 1000),
                            "ssl_days": days, "error": str(e)[:200]})
    return results
