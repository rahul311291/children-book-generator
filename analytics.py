"""
Lightweight funnel analytics + admin notifications.

Logs key events to the `events` collection so the admin dashboard can show,
for every story-creation attempt:
  - who started a story          (story_started)
  - whether they paid            (payment_succeeded)
  - whether the book completed   (book_generated / book_failed)
  - whether they downloaded      (download)
  - whether they requested print (print_requested)

It also emails the admin whenever a print is requested.

Every function here is defensive: a logging or notification failure must
NEVER break the customer-facing flow.
"""
import os
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Funnel event type constants
STORY_STARTED   = "story_started"
PAYMENT_SUCCESS = "payment_succeeded"
BOOK_GENERATED  = "book_generated"
BOOK_FAILED     = "book_failed"
DOWNLOAD        = "download"
PRINT_REQUESTED = "print_requested"


def _conf(key, default=""):
    """Read config from env first, then Streamlit secrets. Never raises."""
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, "")
        except Exception:
            val = ""
    return val or default


def admin_email():
    return _conf("NOTIFY_EMAIL", "rahul.31.shah@gmail.com")


# ── Event logging ────────────────────────────────────────────────────────
def log_event(event_type, email="", user_id="", session_id="", **details):
    """Insert one funnel event. Never raises."""
    try:
        from mongo_client import events_col
        events_col().insert_one({
            "type": event_type,
            "email": (email or "").strip().lower(),
            "user_id": user_id or "",
            "session_id": session_id or "",
            "details": {k: v for k, v in details.items() if v is not None},
            "ts": datetime.utcnow(),
        })
    except Exception as e:
        logger.warning(f"log_event({event_type}) failed: {e}")


# ── Email ────────────────────────────────────────────────────────────────
def send_email(to_email, subject, html):
    """Send an email via the same SMTP config used for OTP sign-in. Returns bool."""
    smtp_user = _conf("GMAIL_USER") or _conf("SMTP_USER")
    smtp_password = _conf("GMAIL_APP_PASSWORD") or _conf("SMTP_PASSWORD")
    smtp_host = _conf("SMTP_HOST", "smtp.gmail.com")
    smtp_port_str = _conf("SMTP_PORT", "465")
    from_email = _conf("SMTP_FROM", smtp_user)
    if not smtp_user or not smtp_password:
        logger.warning("send_email: SMTP not configured (GMAIL_USER/GMAIL_APP_PASSWORD or SMTP_*)")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))
        port = int(smtp_port_str)
        if port == 465:
            with smtplib.SMTP_SSL(smtp_host, 465) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"send_email failed: {e}")
        return False


def notify_print_request(order):
    """Email the admin that a print was requested. `order` is a dict. Returns bool."""
    to = admin_email()
    child   = order.get("child_name", "")
    title   = order.get("story_title", "")
    cust    = order.get("customer_name", "")
    phone   = order.get("phone", "")
    address = order.get("address", "")
    email   = order.get("user_email", "")
    amount  = order.get("amount_paid_inr", "")
    subject = f"New print request - {child or cust or email}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;">
      <h2 style="color:#c2410c;margin-top:0;">New Print &amp; Deliver request</h2>
      <table style="border-collapse:collapse;font-size:14px;line-height:1.6;">
        <tr><td style="padding-right:14px;"><b>Book</b></td><td>{title}</td></tr>
        <tr><td><b>Child</b></td><td>{child}</td></tr>
        <tr><td><b>Customer</b></td><td>{cust}</td></tr>
        <tr><td><b>Phone</b></td><td>{phone}</td></tr>
        <tr><td><b>Email</b></td><td>{email}</td></tr>
        <tr><td><b>Amount</b></td><td>Rs.{amount}</td></tr>
        <tr><td valign="top"><b>Address</b></td><td>{address}</td></tr>
      </table>
      <p style="color:#888;font-size:12px;margin-top:18px;">
        Open the admin Dashboard to manage this order and rebuild the PDF if needed.
      </p>
    </div>"""
    return send_email(to, subject, html)


# ── Dashboard queries ────────────────────────────────────────────────────
def _events():
    from mongo_client import events_col
    return events_col()


def funnel_counts(days=30):
    """Event counts per funnel stage over the last `days` days."""
    out = {STORY_STARTED: 0, PAYMENT_SUCCESS: 0, BOOK_GENERATED: 0,
           DOWNLOAD: 0, PRINT_REQUESTED: 0, BOOK_FAILED: 0}
    try:
        since = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"ts": {"$gte": since}}},
            {"$group": {"_id": "$type", "n": {"$sum": 1}}},
        ]
        for row in _events().aggregate(pipeline):
            if row["_id"] in out:
                out[row["_id"]] = row["n"]
    except Exception as e:
        logger.warning(f"funnel_counts failed: {e}")
    return out


def recent_events(limit=300):
    try:
        return list(_events().find().sort("ts", -1).limit(limit))
    except Exception as e:
        logger.warning(f"recent_events failed: {e}")
        return []


def print_orders(limit=200):
    try:
        from mongo_client import get_db
        return list(get_db()["print_orders"].find().sort("ordered_at", -1).limit(limit))
    except Exception as e:
        logger.warning(f"print_orders failed: {e}")
        return []


def set_print_order_status(order_id, status):
    try:
        from mongo_client import get_db
        get_db()["print_orders"].update_one({"_id": order_id}, {"$set": {"status": status}})
        return True
    except Exception as e:
        logger.warning(f"set_print_order_status failed: {e}")
        return False


def resumable_books(limit=200):
    """Books that have stored images, so their PDF can be rebuilt and re-sent."""
    try:
        from mongo_client import book_history_col
        return list(book_history_col().find(
            {"images": {"$elemMatch": {"$type": "string", "$regex": "^data:image"}}},
            {"_id": 1, "child_name": 1, "title": 1, "metadata": 1,
             "created_at": 1, "user_id": 1},
        ).sort("created_at", -1).limit(limit))
    except Exception as e:
        logger.warning(f"resumable_books failed: {e}")
        return []


def get_book(doc_id):
    try:
        from mongo_client import book_history_col
        return book_history_col().find_one({"_id": doc_id})
    except Exception as e:
        logger.warning(f"get_book failed: {e}")
        return None
