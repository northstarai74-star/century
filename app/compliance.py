import re

from . import brand_rules as R


def _has(text: str, word: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def check_post(caption: str, *, hashtags="", cta="", hero="", bucket="", fmt="", is_creator=False,
               sales_open=False, extra_text="") -> dict:
    """Return {'errors': [...], 'warnings': [...], 'needs_qa': bool, 'needs_md': bool}. Errors block approval."""
    text = f"{caption} {cta} {hashtags} {extra_text}".lower()
    errors, warnings = [], []
    needs_qa = needs_md = False

    for w in R.BANNED:
        if _has(text, w):
            errors.append(f"Banned word/claim: '{w}'")
    for w in R.CERTIFICATIONS:
        if _has(text, w):
            errors.append(f"Certification '{w}' needs QA confirmation for that SKU")
            needs_qa = True
    for w in R.B2B_AND_COMPETITORS:
        if _has(text, w):
            errors.append(f"Never name B2B customers/competitors: '{w}'")
    if "chemical-free" in text or "chemical free" in text:
        errors.append("'Chemical-free' is not allowed; only the jaggery pack says 'No chemicals'")
    if "high protein" in text and "makhana" in text:
        errors.append("Never call makhana 'high protein'")
    if "fat-free" in text and "makhana" in text and any(k in text for k in ("ghee", "roasted in", "recipe")):
        warnings.append("'Fat-free' applies to plain makhana only, not ghee-roasted snacks")
    if "35%" in text and "paneer" in text and "*" not in caption and "*" not in extra_text:
        errors.append("'35% more protein than paneer*' must keep the * and show the footnote basis")
    if "used by" in text:
        errors.append("'Used by …' is not allowed unless the customer gave written permission")

    if not sales_open:
        for b in R.BUY_CTAS:
            if _has(text, b):
                errors.append(f"CTA '{b}' not allowed until the MD sets a sales start date and prices")

    tags = {t.lower() for t in re.findall(r"#\w+", text)}
    for t in R.REQUIRED_HASHTAGS:
        if t not in tags:
            warnings.append(f"Missing brand hashtag {t}")
    if is_creator and not any(t in tags for t in R.ASCI_LABELS):
        errors.append("Paid/gifted creator posts need an ASCI label (#ad, #collab or #sponsored)")

    if any(k in text for k in R.SERVING_WORDS) and "serving suggestion" not in text and fmt in ("reel", "static", "carousel"):
        warnings.append("Prepared-dish visual? Add 'Serving suggestion' on screen")
    if hero and hero.lower() not in R.HEROES | {"brand", "range", "seasoning", "poha", "besan", "pulses"}:
        warnings.append(f"Unknown product bucket '{hero}'")

    if bucket in R.BRAND_LEVEL_BUCKETS:
        needs_md = True
    if re.search(r"\b(250\+|quality parameters)\b", text) and "*" not in caption:
        warnings.append("Keep the asterisk on '250+ quality parameters tested*' and don't explain parameters without QA's list")
    if re.search(r"\biron\b|\bmineral", text):
        errors.append("Iron/mineral claims need lab values + QA sign-off")
        needs_qa = True

    return {"errors": errors, "warnings": warnings, "needs_qa": needs_qa, "needs_md": needs_md}
