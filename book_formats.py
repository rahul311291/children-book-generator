BOOK_FORMATS = [
    {"id": "short", "name": "Short Story", "pages": 6, "emoji": "📗", "desc": "Perfect for bedtime", "detail": "6 pages · ~300 words"},
    {"id": "standard", "name": "Standard Story", "pages": 10, "emoji": "📘", "desc": "Most popular", "detail": "10 pages · ~500 words"},
    {"id": "full", "name": "Full Adventure", "pages": 14, "emoji": "📙", "desc": "Epic journey", "detail": "14 pages · ~700 words"},
]
DEFAULT_FORMAT = BOOK_FORMATS[1]

def get_format_by_id(fmt_id: str) -> dict:
    return next((f for f in BOOK_FORMATS if f["id"] == fmt_id), DEFAULT_FORMAT)

def get_page_count(fmt_id: str) -> int:
    return get_format_by_id(fmt_id)["pages"]
