"""
Admin reporting dashboard.

Shows the full funnel (started -> paid -> book done -> downloaded -> print),
lets the admin manage print requests, and lets the admin rebuild a PDF from a
book's stored images (the "resume" flow) to re-send to a customer manually.

Rendered only for admins, from main()'s page dispatch.
"""
import io
import base64
import logging
import tempfile

import streamlit as st

import analytics

logger = logging.getLogger(__name__)


def _kpi(col, label, value):
    col.markdown(
        f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;
             padding:16px;text-align:center;">
          <div style="font-size:12px;color:#6b7280;">{label}</div>
          <div style="font-size:30px;font-weight:800;color:#1f2937;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _rebuild_pdf_bytes(book):
    """Rebuild a PDF from a stored book_history doc.

    Returns (bytes, filename) on success or (None, error_message) on failure.
    """
    try:
        from PIL import Image
        from main import create_pdf  # deferred import avoids a circular import
        imgs = []
        for s in (book.get("images") or []):
            if isinstance(s, str) and s.startswith("data:image"):
                raw = base64.b64decode(s.split(",", 1)[1])
                imgs.append(Image.open(io.BytesIO(raw)).convert("RGB"))
        if not imgs:
            return None, "This book has no stored images to rebuild from."
        story = book.get("story_data") or {}
        child = book.get("child_name", "Child")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
            create_pdf(story, imgs, child, tf.name, book_format=None)
            path = tf.name
        with open(path, "rb") as fh:
            return fh.read(), f"{child}_Storybook.pdf"
    except Exception as e:
        logger.error(f"_rebuild_pdf_bytes failed: {e}")
        return None, f"Rebuild failed: {e}"


def render_admin_dashboard():
    st.title("Admin Dashboard")
    if st.button("< Back to Main", type="secondary", key="back_from_dashboard"):
        st.session_state.show_admin_dashboard = False
        st.rerun()

    days = st.selectbox(
        "Reporting window", [7, 30, 90, 365], index=1,
        format_func=lambda d: f"Last {d} days",
    )
    f = analytics.funnel_counts(days)

    st.subheader("Funnel")
    cols = st.columns(5)
    _kpi(cols[0], "Started", f["story_started"])
    _kpi(cols[1], "Paid", f["payment_succeeded"])
    _kpi(cols[2], "Book done", f["book_generated"])
    _kpi(cols[3], "Downloaded", f["download"])
    _kpi(cols[4], "Print requests", f["print_requested"])

    def pct(a, b):
        return f"{(100.0 * a / b):.0f}%" if b else "-"

    st.caption(
        f"Pay rate {pct(f['payment_succeeded'], f['story_started'])}  -  "
        f"Completion after pay {pct(f['book_generated'], f['payment_succeeded'])}  -  "
        f"Download rate {pct(f['download'], f['book_generated'])}  -  "
        f"Failed generations: {f['book_failed']}"
    )

    st.divider()
    tab_print, tab_resume, tab_log = st.tabs(
        ["Print requests", "Resume / rebuild PDF", "Event log"]
    )

    # ── Print requests ───────────────────────────────────────────────────
    with tab_print:
        orders = analytics.print_orders()
        if not orders:
            st.info("No print requests yet.")
        for o in orders:
            oid = o.get("_id")
            with st.container(border=True):
                st.markdown(
                    f"**{o.get('story_title', '(book)')}** - for "
                    f"{o.get('child_name', '')}  \n"
                    f"Phone: {o.get('phone', '')}  |  Email: {o.get('user_email', '')}  \n"
                    f"Address: {o.get('address', '')}  \n"
                    f"Rs.{o.get('amount_paid_inr', '')}  |  "
                    f"ordered {o.get('ordered_at', '')}  |  "
                    f"status: **{o.get('status', 'pending')}**"
                )
                b1, b2, b3 = st.columns(3)
                if b1.button("Mark printed", key=f"pr_print_{oid}"):
                    analytics.set_print_order_status(oid, "printed")
                    st.rerun()
                if b2.button("Mark shipped", key=f"pr_ship_{oid}"):
                    analytics.set_print_order_status(oid, "shipped")
                    st.rerun()
                if b3.button("Mark pending", key=f"pr_pend_{oid}"):
                    analytics.set_print_order_status(oid, "pending")
                    st.rerun()

    # ── Resume / rebuild PDF ─────────────────────────────────────────────
    with tab_resume:
        st.caption(
            "If a customer's PDF failed or they couldn't download it, rebuild it "
            "here from the stored images, then send it to them yourself "
            "(e.g. over WhatsApp or email)."
        )
        books = analytics.resumable_books()
        if not books:
            st.info("No books with stored images yet.")
        else:
            labels = {}
            for b in books:
                key = (
                    f"{b.get('child_name', '?')} - "
                    f"{(b.get('title', '') or '')[:40]} "
                    f"({str(b['_id'])[:8]})"
                )
                labels[key] = b["_id"]
            pick = st.selectbox("Choose a book", list(labels.keys()))
            if st.button("Rebuild PDF", type="primary"):
                book = analytics.get_book(labels[pick])
                data, name = _rebuild_pdf_bytes(book or {})
                if data:
                    st.success("PDF rebuilt. Download it and send it to the customer.")
                    st.download_button(
                        "Download rebuilt PDF", data=data, file_name=name,
                        mime="application/pdf", type="primary",
                    )
                    st.caption(f"Customer on file: {(book or {}).get('user_id', '')}")
                else:
                    st.error(name)

    # ── Event log ────────────────────────────────────────────────────────
    with tab_log:
        evs = analytics.recent_events(300)
        if not evs:
            st.info("No events logged yet.")
        else:
            rows = []
            for e in evs:
                d = e.get("details") or {}
                rows.append({
                    "time": e.get("ts"),
                    "event": e.get("type"),
                    "email": e.get("email"),
                    "detail": ", ".join(f"{k}={v}" for k, v in d.items())[:90],
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
