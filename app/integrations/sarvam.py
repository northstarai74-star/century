"""Sarvam AI adapter. Verify endpoints/models against current Sarvam docs before going live."""
import base64

import httpx


class Sarvam:
    def __init__(self, cfg):
        self.key, self.base = cfg.sarvam_key, cfg.sarvam_base.rstrip("/")

    @property
    def live(self):
        return bool(self.key)

    def _h(self):
        return {"api-subscription-key": self.key}

    def transcribe(self, audio: bytes, filename="call.wav", language_code="unknown") -> dict:
        if not self.live:
            return {"dry_run": True, "transcript": "", "language_code": language_code}
        r = httpx.post(f"{self.base}/speech-to-text", headers=self._h(), timeout=60,
                       files={"file": (filename, audio)}, data={"model": "saarika:v2.5", "language_code": language_code})
        r.raise_for_status()
        j = r.json()
        return {"transcript": j.get("transcript", ""), "language_code": j.get("language_code", language_code)}

    def translate(self, text: str, source="auto", target="en-IN") -> str:
        if not self.live:
            return text
        r = httpx.post(f"{self.base}/translate", headers=self._h(), timeout=30,
                       json={"input": text, "source_language_code": source, "target_language_code": target})
        r.raise_for_status()
        return r.json().get("translated_text", text)

    def speak(self, text: str, language_code="hi-IN") -> bytes | None:
        if not self.live:
            return None
        r = httpx.post(f"{self.base}/text-to-speech", headers=self._h(), timeout=60,
                       json={"text": text[:1500], "target_language_code": language_code, "model": "bulbul:v2"})
        r.raise_for_status()
        audios = r.json().get("audios") or []
        return base64.b64decode(audios[0]) if audios else None
