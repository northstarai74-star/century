"""Machine-readable form of docs/brand/Brand_Bible.md sections 7, 10, 12. Update the Bible first."""

BANNED = [
    "diabetic-friendly", "diabetic friendly", "safe for diabetics", "sugar-free", "sugar free", "sugarfree",
    "controls blood sugar", "guilt-free", "guilt free", "detox", "weight loss", "burns fat", "burn fat",
    "boosts immunity", "boost immunity", "immunity booster", "healthier than sugar", "best in india", "purest",
    "100% healthy", "organic", "cures", "cure", "prevents", "prevent", "treats", "treat disease",
    "rich in iron", "cures anaemia",
]
CERTIFICATIONS = ["npop", "nop", "fssc 22000", "fssc22000"]
B2B_AND_COMPETITORS = ["saffola", "marico", "true elements", "trueelements", "chaayos"]
BUY_CTAS = ["buy now", "order now", "shop now", "add to cart", "order today", "buy today"]
ASCI_LABELS = ["#ad", "#collab", "#sponsored"]
REQUIRED_HASHTAGS = ["#century", "#purehomefood", "#centurysince1980"]
HEROES = {"jaggery", "soya", "makhana"}
SERVING_WORDS = ["recipe", "kheer", "curry", "pulao", "keema", "tikka", "chilla", "pakode", "poha"]

CHEMICAL_FREE_OK = False  # only jaggery pack says "No chemicals"
ALLOWED_CTAS_PRE_SALES = ["follow", "save", "share", "thecentury.in", "whatsapp"]
BRAND_LEVEL_BUCKETS = {"brand"}

# Replies we may send automatically. Keys are categories; text is the approved wording (Bible section 11).
REPLY_BANK = {
    "diabetic": "Jaggery is still a form of sugar, so we don't recommend it as a sugar substitute for diabetes. Please check with your doctor.",
    "organic": "This pack isn't sold as certified organic. Every batch is quality-checked before packing, and the QR on the pack shows which of our own plants made it.",
    "darker": "Natural jaggery colour changes with the cane and the season. We don't add colour or chemical whiteners to make it look lighter.",
    "soya_safety": "Soya is a widely eaten plant protein and is considered safe as part of a balanced diet for most people. If you have a specific medical condition, please check with your doctor.",
    "where_buy_pre": "Launching very soon in Delhi NCR. Follow us or join our WhatsApp list to hear first.",
    "where_buy": "Order on WhatsApp at {whatsapp_number}.",
    "price_loose": "You're paying for what's not in it: unpolished, cleaned and checked on 250+ quality parameters before packing.",
    "freshness": "Check the Use By date on the pack. Once opened, keep it in an airtight container.",
    "complaint": "We're sorry, that's not the Century standard. Please DM us your batch number and a photo, and we'll sort it out quickly.",
    "contact": "You can reach us on 1800 296 7999 or century@thecentury.in.",
}

# Keyword classifier -> category. Order matters. 'escalate' categories never auto-reply.
CLASSIFY = [
    ("legal", ["legal", "lawyer", "court", "fssai", "consumer forum", "sue ", "notice"], "md"),
    ("health_incident", ["hospital", "food poisoning", "vomit", "allergic reaction", "sick after"], "md"),
    ("media", ["journalist", "press", "media", "interview"], "md"),
    ("complaint", ["complaint", "bad quality", "stale", "insect", "fungus", "worm", "expired", "smell", "damaged", "wrong item", "kharab", "ganda"], "qa"),
    ("diabetic", ["diabet", "sugar patient", "blood sugar"], None),
    ("organic", ["organic"], None),
    ("darker", ["darker", "dark colour", "dark color", "kala gud"], None),
    ("soya_safety", ["hormone", "soya safe", "soy safe", "is soya"], None),
    ("price_loose", ["why pay more", "costly", "expensive", "mehenga", "mahanga"], None),
    ("freshness", ["how long", "shelf life", "stay fresh", "expiry", "use by"], None),
    ("where_buy", ["where to buy", "where can i buy", "kahan milega", "kaha milega", "buy", "order", "price", "rate", "available", "kitne ka"], None),
    ("contact", ["phone number", "contact", "call you", "email"], None),
]
ABUSE = ["spam", "http://", "https://bit.ly", "click here", "free followers", "mc ", "bc ", "madarchod", "bhenchod"]
