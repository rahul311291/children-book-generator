"""
Cashfree Payment Links integration for the children's book generator.

Configure via env vars or Streamlit secrets:
  CASHFREE_APP_ID      — App ID (Key ID)
  CASHFREE_SECRET_KEY  — Secret Key
  CASHFREE_ENV         — "sandbox" (default) or "production"
  APP_BASE_URL         — public URL of the app (used as payment return URL)

Pricing tiers (INR): basic template 149, personalized 249, premium print 699.
"""

import os
import re
import uuid
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)

FREE_IMAGES_PER_BOOK = 3
PRICE_PER_PAGE_INR = 15  # kept for legacy per-page calc

# Custom story — two-gate pricing
# Live (promotional) and regular (strikethrough) prices.
# Show both in the UI so the customer sees the saving.
CUSTOM_STORY_PRICE_INR         = 199    # Promotional live price for digital download
CUSTOM_STORY_REGULAR_PRICE_INR = 350    # Strikethrough / "original" price
CUSTOM_DOWNLOAD_PRICE_INR      = 650    # Print & Deliver price (unchanged)

# Legacy flat pricing (kept for any existing references)
PDF_PRICE_INR = CUSTOM_DOWNLOAD_PRICE_INR
PRINT_PRICE_INR = CUSTOM_DOWNLOAD_PRICE_INR

# Template tiers
TEMPLATE_BASIC_INR = 149
TEMPLATE_PERSONALIZED_INR = 249
TEMPLATE_PREMIUM_INR = 699

# Legacy aliases (used by existing code)
CUSTOM_BOOK_PRICE_INR = CUSTOM_STORY_PRICE_INR
TEMPLATE_BOOK_PRICE_INR = TEMPLATE_BASIC_INR

CF_API_VERSION = "2023-08-01"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _conf(key: str, default: str = "") -> str:
    """Read a config value from env vars first, then Streamlit secrets."""
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            val = str(st.secrets.get(key, "") or "")
        except Exception:
            val = ""
    return (val or default).strip()


def _cf_cfg() -> dict:
    app_id = _conf("CASHFREE_APP_ID")
    secret = _conf("CASHFREE_SECRET_KEY")
    env = _conf("CASHFREE_ENV", "sandbox").lower()
    if env not in ("sandbox", "production"):
        env = "sandbox"
    base = "https://api.cashfree.com" if env == "production" else "https://sandbox.cashfree.com"
    return {"app_id": app_id, "secret": secret, "env": env, "base": base}


def app_base_url() -> str:
    return _conf("APP_BASE_URL").rstrip("/")


def is_cashfree_configured() -> bool:
    c = _cf_cfg()
    return bool(c["app_id"] and c["secret"])


def cashfree_diagnostics() -> dict:
    """Admin-facing config health check (never exposes secret values)."""
    c = _cf_cfg()
    return {
        "app_id_set": bool(c["app_id"]),
        "secret_set": bool(c["secret"]),
        "environment": c["env"],
        "api_base": c["base"],
        "app_base_url": app_base_url() or "(not set — return-to-app redirect disabled)",
    }


def _headers() -> dict:
    c = _cf_cfg()
    return {
        "x-client-id": c["app_id"],
        "x-client-secret": c["secret"],
        "x-api-version": CF_API_VERSION,
        "Content-Type": "application/json",
    }


def normalize_phone(phone: str) -> str:
    """Strip a phone number to digits (keeps last 10 for Indian numbers)."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[-10:]
    return digits


def is_valid_phone(phone: str) -> bool:
    digits = normalize_phone(phone)
    return len(digits) == 10 and digits[0] in "6789"


# ---------------------------------------------------------------------------
# Credit helpers (balance stored in paise: 1 INR = 100 paise)
# ---------------------------------------------------------------------------

def get_user_balance_paise(user_id: str) -> int:
    try:
        from mongo_client import users_col
        user = users_col().find_one({"_id": user_id}, {"credits": 1})
        return int((user or {}).get("credits", 0))
    except Exception as e:
        logger.error(f"get_user_balance_paise: {e}")
        return 0


def get_user_balance_inr(user_id: str) -> float:
    return get_user_balance_paise(user_id) / 100


def deduct_credits(user_id: str, amount_paise: int) -> bool:
    try:
        from mongo_client import users_col
        result = users_col().update_one(
            {"_id": user_id, "credits": {"$gte": amount_paise}},
            {"$inc": {"credits": -amount_paise}},
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"deduct_credits: {e}")
        return False


def add_credits(user_id: str, amount_paise: int) -> bool:
    try:
        from mongo_client import users_col
        users_col().update_one({"_id": user_id}, {"$inc": {"credits": amount_paise}})
        return True
    except Exception as e:
        logger.error(f"add_credits: {e}")
        return False


def book_price_inr(page_count: int) -> int:
    return PRICE_PER_PAGE_INR * page_count


def book_price_paise(page_count: int) -> int:
    return book_price_inr(page_count) * 100


def custom_book_price_inr() -> int:
    return CUSTOM_BOOK_PRICE_INR


def template_book_price_inr() -> int:
    return TEMPLATE_BOOK_PRICE_INR


def pdf_price_inr() -> int:
    return PDF_PRICE_INR


def print_price_inr() -> int:
    return PRINT_PRICE_INR


def custom_story_regular_price_inr() -> int:
    """Strikethrough 'original' price for digital PDF. Display only — not charged."""
    return CUSTOM_STORY_REGULAR_PRICE_INR


def custom_story_promo_off_pct() -> int:
    """Promotional discount % to display next to the strikethrough."""
    reg = CUSTOM_STORY_REGULAR_PRICE_INR
    live = CUSTOM_STORY_PRICE_INR
    if reg <= 0 or live >= reg:
        return 0
    return round((reg - live) * 100 / reg)


def custom_story_price_inr() -> int:
    """Download option — promotional digital PDF price."""
    return CUSTOM_STORY_PRICE_INR


def custom_download_price_inr() -> int:
    """Print & Deliver option — ₹650 printed book + digital."""
    return CUSTOM_DOWNLOAD_PRICE_INR


def cashfree_env() -> str:
    """Return 'sandbox' or 'production' (used by the JS SDK)."""
    return _cf_cfg()["env"]


# ---------------------------------------------------------------------------
# Cashfree Orders API — gateway checkout (preferred over Payment Links)
# ---------------------------------------------------------------------------

def create_cashfree_order(
    user_id: str,
    user_email: str,
    amount_inr: int,
    purpose: str,
    customer_phone: str,
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    """
    Create a Cashfree order via the Orders API.
    Returns {'order_id', 'payment_session_id'} on success, or {'error': msg} on failure.
    The payment_session_id is passed to the JS Drop-in Checkout SDK.
    """
    if not is_cashfree_configured():
        return {"error": "Payment gateway not configured. Please contact support."}

    phone = normalize_phone(customer_phone)
    if not is_valid_phone(phone):
        return {"error": "A valid 10-digit mobile number is required for payment."}

    c = _cf_cfg()
    order_id = f"cbg_{user_id[:8]}_{uuid.uuid4().hex[:10]}"

    # Return URL — Cashfree redirects here after embedded form completes
    # We pass the order_id so Streamlit can verify on return
    # Try STREAMLIT_URL first (legacy), then APP_BASE_URL (canonical), then
    # st.secrets. If NOTHING is set, return an error rather than fall through
    # to a hardcoded URL — silently using a stale URL would break the payment
    # return path AND leak the URL pattern into logs.
    _app_url = os.environ.get("STREAMLIT_URL", "") or os.environ.get("APP_BASE_URL", "")
    if not _app_url:
        try:
            import streamlit as _st
            _app_url = (
                _st.secrets.get("STREAMLIT_URL", "")
                or _st.secrets.get("APP_BASE_URL", "")
            )
        except Exception:
            _app_url = ""
    if not _app_url:
        return {
            "error": "Server misconfigured: APP_BASE_URL is not set. "
                     "Set it in Streamlit secrets so payment returns work."
        }
    _app_url = _app_url.rstrip("/")
    _return_url = f"{_app_url}/?cf_order_id={order_id}&cf_status=SUCCESS"

    payload = {
        "order_id": order_id,
        "order_amount": float(amount_inr),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": (user_id or "guest")[:50],
            "customer_name": user_email.split("@")[0],
            "customer_email": user_email,
            "customer_phone": phone,
        },
        "order_note": purpose[:255],
        "order_meta": {
            "return_url": _return_url,
            "notify_url": "",   # webhook URL — leave blank unless configured
        },
    }

    try:
        r = requests.post(
            f"{c['base']}/pg/orders",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        try:
            data = r.json()
        except ValueError:
            data = {}

        if r.status_code in (200, 201) and data.get("payment_session_id"):
            _save_pending_order(user_id, order_id, amount_inr, purpose, metadata)
            return {
                "order_id": order_id,
                "payment_session_id": data["payment_session_id"],
            }

        error_msg = data.get("message", "") or data.get("error", "")
        logger.error(f"Cashfree create order failed {r.status_code} [{c['env']}]: {data}")
        if r.status_code == 401:
            return {"error": (
                f"Payment gateway authentication failed. Check that API keys match "
                f"the configured environment ('{c['env']}')."
            )}
        return {"error": f"Payment service error: {error_msg}" if error_msg else "Order creation failed. Please try again."}

    except requests.exceptions.Timeout:
        return {"error": "Payment service timed out. Please try again."}
    except Exception as e:
        logger.error(f"create_cashfree_order error: {e}")
        return {"error": "Could not connect to payment service. Please try again later."}


def verify_cashfree_order(order_id: str) -> str:
    """
    Fetch a Cashfree order and return its status string.
    Common values: 'PAID', 'ACTIVE', 'EXPIRED', 'TERMINATED'.
    Returns 'ERROR' if the call fails.
    """
    if not is_cashfree_configured():
        return "ERROR"
    c = _cf_cfg()
    try:
        r = requests.get(
            f"{c['base']}/pg/orders/{order_id}",
            headers=_headers(),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            status = (data.get("order_status") or "ACTIVE").upper()
            logger.info(f"verify_cashfree_order {order_id} → {status}")
            return status
        logger.warning(f"verify_cashfree_order {order_id}: HTTP {r.status_code}")
        return "ERROR"
    except Exception as e:
        logger.error(f"verify_cashfree_order {order_id}: {e}")
        return "ERROR"


def user_can_afford_book(user_id: str, page_count: int) -> bool:
    return get_user_balance_paise(user_id) >= book_price_paise(page_count)


# ---------------------------------------------------------------------------
# Purchases (entitlements) — survive sessions, unlock content after payment
# ---------------------------------------------------------------------------

def record_purchase(user_id: str, link_id: str, amount_inr: int, metadata: dict) -> None:
    try:
        from mongo_client import purchases_col
        purchases_col().update_one(
            {"link_id": link_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "link_id": link_id,
                "amount_inr": amount_inr,
                "template_id": (metadata or {}).get("template_id", ""),
                "tier": (metadata or {}).get("tier", ""),
                "child_name": (metadata or {}).get("child_name", ""),
                "book_kind": (metadata or {}).get("book_kind", "template"),
                "purpose": (metadata or {}).get("purpose", ""),
                # Top-level for fast lookup — used by has_paid_for_book to
                # link a purchase to a specific book_history row, and to
                # tell download from print+deliver on payment-status restore.
                "book_history_id": (metadata or {}).get("book_history_id", ""),
                "gate": (metadata or {}).get("gate", ""),
                "paid_at": datetime.utcnow(),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"record_purchase: {e}")


def has_purchased_template(user_id: str, template_id: str, child_name: str = "") -> Optional[dict]:
    """Return the purchase doc if user already bought this template (optionally for this child)."""
    try:
        from mongo_client import purchases_col
        q = {"user_id": user_id, "template_id": template_id}
        if child_name:
            q["child_name"] = child_name
        return purchases_col().find_one(q, sort=[("paid_at", -1)])
    except Exception as e:
        logger.error(f"has_purchased_template: {e}")
        return None


def get_user_purchases(user_id: str) -> list:
    try:
        from mongo_client import purchases_col
        return list(purchases_col().find({"user_id": user_id}).sort("paid_at", -1))
    except Exception as e:
        logger.error(f"get_user_purchases: {e}")
        return []


def has_paid_for_book(user_id: str, book_history_id: str = "", child_name: str = "",
                      book_kind: str = "custom") -> Optional[dict]:
    """Return the most recent purchase for this (user, book) or None.

    Two-stage lookup:
      1. Direct match by book_history_id (set on every order created after
         this fix landed).
      2. Fallback: match by (user_id, child_name, book_kind) for purchases
         recorded before we started writing book_history_id into metadata.

    The returned doc has 'gate' which the caller uses to pick the right
    payment_status / delivery_option on restore (story_paid + download vs.
    print_paid + print_deliver).
    """
    try:
        from mongo_client import purchases_col
        if book_history_id:
            doc = purchases_col().find_one(
                {"user_id": user_id, "book_history_id": book_history_id},
                sort=[("paid_at", -1)],
            )
            if doc:
                return doc
        if child_name:
            doc = purchases_col().find_one(
                {"user_id": user_id, "child_name": child_name, "book_kind": book_kind},
                sort=[("paid_at", -1)],
            )
            if doc:
                return doc
        return None
    except Exception as e:
        logger.error(f"has_paid_for_book: {e}")
        return None



# ---------------------------------------------------------------------------
# Payment link creation
# ---------------------------------------------------------------------------

def create_payment_link(
    user_id: str,
    user_email: str,
    amount_inr: int,
    purpose: str,
    return_url: str = "",
    customer_phone: str = "",
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    """
    Create a Cashfree Payment Link.
    Returns {'link_url', 'link_id'} on success, or {'error': msg} on failure.
    """
    if not is_cashfree_configured():
        logger.error("Cashfree not configured — CASHFREE_APP_ID or CASHFREE_SECRET_KEY missing")
        return {"error": "Payment gateway not configured. Please contact support."}

    phone = normalize_phone(customer_phone)
    if not is_valid_phone(phone):
        return {"error": "A valid 10-digit mobile number is required for payment."}

    c = _cf_cfg()
    link_id = f"cbg_{user_id[:8]}_{uuid.uuid4().hex[:8]}"

    if not return_url:
        base = app_base_url()
        if base:
            return_url = f"{base}/?cf_link_id={link_id}"

    payload = {
        "link_id": link_id,
        "link_amount": float(amount_inr),
        "link_currency": "INR",
        "link_purpose": purpose[:500],
        "customer_details": {
            "customer_phone": phone,
            "customer_email": user_email,
            "customer_name": user_email.split("@")[0],
        },
        "link_expiry_time": (datetime.utcnow() + timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "link_notify": {"send_sms": False, "send_email": True},
        "link_auto_reminders": True,
    }
    if return_url:
        payload["link_meta"] = {"return_url": return_url}

    try:
        r = requests.post(f"{c['base']}/pg/links", headers=_headers(), json=payload, timeout=30)
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code in (200, 201) and data.get("link_url"):
            _save_pending_order(user_id, link_id, amount_inr, purpose, metadata)
            save_pending_payment_for_reminders(
                user_id=user_id,
                user_email=user_email,
                amount_inr=amount_inr,
                book_title=purpose,
                payment_link_id=link_id,
                payment_link_url=data["link_url"],
            )
            return {"link_url": data["link_url"], "link_id": link_id}
        error_msg = data.get("message", "") or data.get("error", "")
        logger.error(f"Cashfree create link failed {r.status_code} [{c['env']}]: {data}")
        if r.status_code == 401:
            return {"error": (
                "Payment gateway authentication failed. The API keys do not match the "
                f"configured environment ('{c['env']}'). If you are using production keys, "
                "set CASHFREE_ENV=production in your secrets."
            )}
        return {"error": f"Payment service error: {error_msg}" if error_msg else "Payment link creation failed. Please try again."}
    except requests.exceptions.Timeout:
        logger.error("Cashfree request timed out")
        return {"error": "Payment service timed out. Please try again."}
    except Exception as e:
        logger.error(f"create_payment_link error: {e}")
        return {"error": "Could not connect to payment service. Please try again later."}


def _save_pending_order(user_id: str, link_id: str, amount_inr: int, purpose: str,
                        metadata: Optional[dict] = None):
    try:
        from mongo_client import get_db
        get_db()["payment_orders"].insert_one({
            "_id": link_id,
            "user_id": user_id,
            "amount_inr": amount_inr,
            "amount_paise": amount_inr * 100,
            "purpose": purpose,
            "metadata": metadata or {},
            "status": "PENDING",
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        logger.warning(f"_save_pending_order: {e}")


def get_order(link_id: str) -> Optional[dict]:
    try:
        from mongo_client import get_db
        return get_db()["payment_orders"].find_one({"_id": link_id})
    except Exception as e:
        logger.error(f"get_order: {e}")
        return None


def save_pending_payment_for_reminders(
    user_id: str,
    user_email: str,
    amount_inr: int,
    child_name: str = "",
    book_title: str = "",
    product_type: str = "pdf",
    template_id: str = "",
    payment_link_id: str = "",
    payment_link_url: str = "",
):
    """Save pending payment to MongoDB for automated email reminders."""
    try:
        from mongo_client import get_db
        get_db()["pending_payments"].insert_one({
            "user_id": user_id,
            "user_email": user_email,
            "amount_inr": amount_inr,
            "child_name": child_name,
            "book_title": book_title,
            "product_type": product_type,
            "template_id": template_id,
            "payment_link_id": payment_link_id,
            "payment_link_url": payment_link_url,
            "reminder_1h_sent": False,
            "reminder_9h_sent": False,
            "reminder_24h_sent": False,
            "paid": False,
            "created_at": datetime.utcnow(),
        })
        logger.info(f"Pending payment saved for reminders: {user_email}")
    except Exception as e:
        logger.warning(f"save_pending_payment_for_reminders: {e}")


def mark_payment_complete_for_reminders(payment_link_id: str):
    """Mark a pending payment as paid in MongoDB to stop reminders."""
    try:
        from mongo_client import get_db
        get_db()["pending_payments"].update_one(
            {"payment_link_id": payment_link_id},
            {"$set": {"paid": True, "paid_at": datetime.utcnow()}},
        )
    except Exception as e:
        logger.warning(f"mark_payment_complete_for_reminders: {e}")


# ---------------------------------------------------------------------------
# Payment status check
# ---------------------------------------------------------------------------

def check_payment_status(link_id: str) -> str:
    """Returns 'PAID', 'PENDING', 'EXPIRED', or 'ERROR'."""
    if not is_cashfree_configured():
        return "ERROR"
    c = _cf_cfg()
    try:
        r = requests.get(
            f"{c['base']}/pg/links/{link_id}", headers=_headers(), timeout=15
        )
        data = r.json()
        if r.status_code == 200:
            status = data.get("link_status", "ACTIVE")
            if status == "PAID":
                return "PAID"
            elif status in ("ACTIVE", "PARTIALLY_PAID"):
                return "PENDING"
            else:
                return "EXPIRED"
        logger.warning(f"check_payment_status {link_id}: HTTP {r.status_code} {data}")
        return "ERROR"
    except Exception as e:
        logger.error(f"check_payment_status {link_id}: {e}")
        return "ERROR"


def confirm_payment_and_credit(order_or_link_id: str, user_id: str) -> bool:
    """
    Verify payment with Cashfree and credit the user. Idempotent.
    Works for both Cashfree Payment Links (legacy) and Orders API orders.
    Orders created via create_cashfree_order() have IDs starting with 'cbg_'.
    """
    link_id = order_or_link_id
    try:
        from mongo_client import get_db
        orders = get_db()["payment_orders"]
        order = orders.find_one({"_id": link_id, "user_id": user_id})
        if not order:
            # Also accept without user_id match (e.g. JS callback path)
            order = orders.find_one({"_id": link_id})
        if not order:
            return False
        if order.get("status") == "CREDITED":
            return True  # Already processed

        # Route to correct API: Orders API for cbg_ prefixed IDs, Links API otherwise
        if link_id.startswith("cbg_"):
            cf_status = verify_cashfree_order(link_id)
        else:
            cf_status = check_payment_status(link_id)
        if cf_status == "PAID":
            add_credits(user_id, order["amount_paise"])
            orders.update_one(
                {"_id": link_id},
                {"$set": {"status": "CREDITED", "credited_at": datetime.utcnow()}},
            )
            meta = dict(order.get("metadata") or {})
            meta.setdefault("purpose", order.get("purpose", ""))
            record_purchase(user_id, link_id, order.get("amount_inr", 0), meta)
            mark_payment_complete_for_reminders(link_id)
            return True
        return False
    except Exception as e:
        logger.error(f"confirm_payment_and_credit: {e}")
        return False


# ---------------------------------------------------------------------------
# Wizard / story snapshot — survives the Cashfree payment redirect on mobile
# ---------------------------------------------------------------------------
# On mobile the user is taken away from the app (top-level redirect → Cashfree
# → UPI app → back). When they return, Streamlit may serve a fresh
# st.session_state (worker restart, expired cookie, different session cookie
# after the auth round-trip). Without this snapshot, st.session_state.generated_story
# is None on return and the rendering tree falls back to the home page even
# though the payment toast fires. We persist what we need keyed by order_id and
# rehydrate inside the cf_status=SUCCESS handler in main.py.

def save_book_snapshot(order_id: str, user_id: str, snapshot: dict) -> None:
    try:
        from mongo_client import get_db
        get_db()["book_snapshots"].update_one(
            {"_id": order_id},
            {"$set": {
                "user_id": user_id,
                "snapshot": snapshot,
                "created_at": datetime.utcnow(),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"save_book_snapshot: {e}")


def load_book_snapshot(order_id: str) -> Optional[dict]:
    try:
        from mongo_client import get_db
        doc = get_db()["book_snapshots"].find_one({"_id": order_id})
        return doc.get("snapshot") if doc else None
    except Exception as e:
        logger.warning(f"load_book_snapshot: {e}")
        return None
