"""
Cashfree Payment Links integration for the children's book generator.

Configure via env vars or Streamlit secrets:
  CASHFREE_APP_ID      — App ID (Key ID)
  CASHFREE_SECRET_KEY  — Secret Key
  CASHFREE_ENV         — "sandbox" (default) or "production"

Pricing: FREE_IMAGES_PER_BOOK images free; full book = PRICE_PER_PAGE × page_count INR.
"""

import os
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

# Flat pricing
CUSTOM_BOOK_PRICE_INR = 1100   # wizard-generated custom book with AI images
TEMPLATE_BOOK_PRICE_INR = 300  # template book (pre-designed)

CF_API_VERSION = "2023-08-01"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _cf_cfg() -> dict:
    app_id = os.getenv("CASHFREE_APP_ID", "")
    secret = os.getenv("CASHFREE_SECRET_KEY", "")
    env = os.getenv("CASHFREE_ENV", "sandbox")
    try:
        import streamlit as st
        app_id = app_id or str(st.secrets.get("CASHFREE_APP_ID", "") or "")
        secret = secret or str(st.secrets.get("CASHFREE_SECRET_KEY", "") or "")
        env = env or str(st.secrets.get("CASHFREE_ENV", "sandbox") or "sandbox")
    except Exception:
        pass
    base = "https://api.cashfree.com" if env == "production" else "https://sandbox.cashfree.com"
    return {"app_id": app_id, "secret": secret, "base": base}


def is_cashfree_configured() -> bool:
    c = _cf_cfg()
    return bool(c["app_id"] and c["secret"])


def _headers() -> dict:
    c = _cf_cfg()
    return {
        "x-client-id": c["app_id"],
        "x-client-secret": c["secret"],
        "x-api-version": CF_API_VERSION,
        "Content-Type": "application/json",
    }


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


def user_can_afford_book(user_id: str, page_count: int) -> bool:
    return get_user_balance_paise(user_id) >= book_price_paise(page_count)


# ---------------------------------------------------------------------------
# Payment link creation
# ---------------------------------------------------------------------------

def create_payment_link(
    user_id: str,
    user_email: str,
    amount_inr: int,
    purpose: str,
    return_url: str = "",
) -> Optional[dict]:
    """
    Create a Cashfree Payment Link. Returns dict with 'link_url' and 'link_id',
    or None on failure.
    """
    if not is_cashfree_configured():
        logger.error("Cashfree not configured")
        return None
    c = _cf_cfg()
    link_id = f"cbg_{user_id[:8]}_{uuid.uuid4().hex[:8]}"
    payload = {
        "link_id": link_id,
        "link_amount": float(amount_inr),
        "link_currency": "INR",
        "link_purpose": purpose,
        "customer_details": {
            "customer_phone": "9999999999",  # required by Cashfree; user may update later
            "customer_email": user_email,
            "customer_name": user_email.split("@")[0],
        },
        "link_expiry_time": (datetime.utcnow() + timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "link_notify": {"send_sms": False, "send_email": False},
    }
    if return_url:
        payload["link_meta"] = {"return_url": return_url}
    try:
        r = requests.post(f"{c['base']}/pg/links", headers=_headers(), json=payload, timeout=30)
        data = r.json()
        if r.status_code in (200, 201) and data.get("link_url"):
            # Store order in DB for later status checking
            _save_pending_order(user_id, link_id, amount_inr, purpose)
            return {"link_url": data["link_url"], "link_id": link_id}
        logger.error(f"Cashfree create link failed {r.status_code}: {data}")
        return None
    except Exception as e:
        logger.error(f"create_payment_link error: {e}")
        return None


def _save_pending_order(user_id: str, link_id: str, amount_inr: int, purpose: str):
    try:
        from mongo_client import get_db
        get_db()["payment_orders"].insert_one({
            "_id": link_id,
            "user_id": user_id,
            "amount_inr": amount_inr,
            "amount_paise": amount_inr * 100,
            "purpose": purpose,
            "status": "PENDING",
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        logger.warning(f"_save_pending_order: {e}")


# ---------------------------------------------------------------------------
# Payment status check
# ---------------------------------------------------------------------------

def check_payment_status(link_id: str) -> str:
    """
    Returns 'PAID', 'PENDING', 'EXPIRED', or 'ERROR'.
    """
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
            # PAID → link fully paid; ACTIVE → waiting; EXPIRED → timed out
            if status == "PAID":
                return "PAID"
            elif status in ("ACTIVE", "PARTIALLY_PAID"):
                return "PENDING"
            else:
                return "EXPIRED"
        return "ERROR"
    except Exception as e:
        logger.error(f"check_payment_status {link_id}: {e}")
        return "ERROR"


def confirm_payment_and_credit(link_id: str, user_id: str) -> bool:
    """
    Poll Cashfree for payment status. On PAID, add credits and mark order complete.
    Returns True if payment confirmed and credits added.
    """
    try:
        from mongo_client import get_db
        orders = get_db()["payment_orders"]
        order = orders.find_one({"_id": link_id, "user_id": user_id})
        if not order:
            return False
        if order.get("status") == "CREDITED":
            return True  # Already processed

        cf_status = check_payment_status(link_id)
        if cf_status == "PAID":
            add_credits(user_id, order["amount_paise"])
            orders.update_one(
                {"_id": link_id},
                {"$set": {"status": "CREDITED", "credited_at": datetime.utcnow()}},
            )
            return True
        return False
    except Exception as e:
        logger.error(f"confirm_payment_and_credit: {e}")
        return False
