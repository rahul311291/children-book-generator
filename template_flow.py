"""
Customer-facing template flow + admin Template Studio.

Customer journey:
  Gallery → Preview (3 free pages, rest locked) → Customize (name, gender,
  age, phone, optional photo) → Pay (Cashfree link) → Instant book from
  pre-rendered assets (basic) or photo-personalized re-render (personalized).

Entitlements live in the `purchases` collection — once paid, the customer
can always rebuild/download their book without paying again.

NOTE: this module must never import main (circular). main.py passes
save_history_cb into render_template_mode.
"""

import logging
import os
import base64
from typing import Callable, Optional

import streamlit as st
import streamlit.components.v1 as components

import template_store
from template_store import (
    build_book_from_assets,
    personalize_book_with_photo,
    template_coverage,
    generate_assets_for_template,
    asset_status,
    AGE_GROUPS,
    GENDERS,
)
from template_book_generator import (
    get_available_templates,
    get_template_pages,
    display_template_book_preview,
    convert_uploaded_file_to_base64,
)
from payments import (
    create_cashfree_order,
    verify_cashfree_order,
    cashfree_dropin_html,
    confirm_payment_and_credit,
    has_purchased_template,
    is_valid_phone,
    cashfree_diagnostics,
    TEMPLATE_BASIC_INR,
    TEMPLATE_PERSONALIZED_INR,
)

logger = logging.getLogger(__name__)

FREE_PREVIEW_PAGES = 3

TIERS = {
    "basic": {
        "label": "Digital Book",
        "price": TEMPLATE_BASIC_INR,
        "desc": "Instant personalized e-book with your child's name woven into every page.",
    },
    "personalized": {
        "label": "Photo Personalized",
        "price": TEMPLATE_PERSONALIZED_INR,
        "desc": "Upload a photo — we illustrate your child as the hero of the story.",
    },
}

_GALLERY_CSS = """
<style>
.tpl-card-link { text-decoration: none !important; color: inherit !important;
  display: block; cursor: pointer; }
.tpl-card-link:hover .tpl-card { box-shadow: 0 8px 20px rgba(0,0,0,0.10);
  transform: translateY(-2px); }
.tpl-card { border: 1px solid #eee; border-radius: 16px; overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-bottom: 8px; background: #fff;
  transition: box-shadow .15s ease, transform .15s ease; }
.tpl-card img { width: 100%; aspect-ratio: 3/4; object-fit: cover; display: block; }
.tpl-card-body { padding: 12px 14px; }
.tpl-card-body h4 { margin: 0 0 4px 0; font-size: 1.05rem; min-height: 2.5rem;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.tpl-card-body p { color: #777; font-size: 0.85rem; margin: 0 0 8px 0; min-height: 2.4rem;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.tpl-price { color: #FF6B6B; font-weight: 700; }
.tpl-locked { position: relative; filter: blur(6px); }
.tpl-peek-img { width: 100%; aspect-ratio: 3/4; object-fit: cover; border-radius: 12px;
  display: block; box-shadow: 0 6px 16px rgba(42,36,32,0.10); }
.tpl-peek-ph { width: 100%; aspect-ratio: 3/4; border-radius: 12px;
  background: linear-gradient(135deg,#F4E7DC,#E7EFE9);
  display: flex; align-items: center; justify-content: center; }
.tpl-peek-ph span { font-size: 12.5px; color: #8A7C6C; }
</style>
"""


def _sample_page_image(template_id: str, page_number: int,
                       gender: str, age: int,
                       remote_cover: str = "") -> Optional[str]:
    """Sample image for a sneak-peek page.

    Sneak peek samples come ONLY from admin pre-rendered template assets —
    the ones generated in Template Studio. We deliberately do not fall
    through to image_pool, book_history, or the bundled cover so that:
      * Every visitor sees the same canonical samples regardless of who
        is logged in or what they have generated themselves.
      * The cover image is not repeated across all preview slots when
        admin pre-rendering is incomplete for a page.
    Returns None if admin has not pre-rendered that page — caller renders
    a placeholder so the gap is visible (and Template Studio can fill it).

    `remote_cover` is kept in the signature for backwards compatibility
    with older call sites but is intentionally unused.
    """
    del remote_cover  # unused — kept for signature stability
    try:
        return template_store.get_asset(template_id, page_number, gender, age)
    except Exception:
        return None


def _reset_flow(keep_template: bool = False):
    for k in [
        "tpl_book_data", "tpl_cf_order_id", "tpl_cf_session",
        "tpl_tier", "tpl_form", "tpl_building",
    ]:
        st.session_state.pop(k, None)
    if not keep_template:
        st.session_state.pop("tpl_selected_id", None)


# ---------------------------------------------------------------------------
# Customer flow
# ---------------------------------------------------------------------------

_COVER_BY_ID = {
    "a1111111-1111-1111-1111-111111111111": "01_when_i_grow_up.png",
    "a2222222-2222-2222-2222-222222222222": "02_snow_white.png",
    "a3333333-3333-3333-3333-333333333333": "03_cricket_champion.png",
    "a4444444-4444-4444-4444-444444444444": "04_cinderella.png",
    "a5555555-5555-5555-5555-555555555555": "05_sports_day.png",
    "a6666666-6666-6666-6666-666666666666": "06_space_adventure.png",
    "a7777777-7777-7777-7777-777777777777": "07_world_of_friends.png",
    "a8888888-8888-8888-8888-888888888888": "08_alphabet.png",
}
_COVER_CACHE = {}


def _local_cover_uri(template_id: str) -> str:
    """Return a data-URI for our bundled cover art for this template, or ''."""
    if template_id in _COVER_CACHE:
        return _COVER_CACHE[template_id]
    uri = ""
    fn = _COVER_BY_ID.get(template_id)
    if fn:
        path = os.path.join(os.path.dirname(__file__), "assets", "sample_covers", fn)
        try:
            with open(path, "rb") as f:
                uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()
        except Exception:
            uri = ""
    _COVER_CACHE[template_id] = uri
    return uri


def render_template_mode(api_key: str, save_history_cb: Optional[Callable] = None):
    """Entry point for the template experience (called from main.py)."""
    st.markdown(_GALLERY_CSS, unsafe_allow_html=True)

    # Card-click navigation: any tile that links to ?tpl=<id> lands here.
    # We move the value into session_state, clear the param, then rerun so
    # downstream logic behaves identically to clicking the Preview button.
    try:
        qp_tpl = st.query_params.get("tpl")
    except Exception:
        qp_tpl = None
    if qp_tpl and st.session_state.get("tpl_selected_id") != qp_tpl:
        _reset_flow()
        st.session_state.tpl_selected_id = qp_tpl
        try:
            del st.query_params["tpl"]
        except Exception:
            pass
        st.rerun()

    # Finished book → preview screen
    if st.session_state.get("tpl_book_data"):
        _render_finished_book(api_key, save_history_cb)
        return

    template_id = st.session_state.get("tpl_selected_id")
    if not template_id:
        _render_gallery()
        return

    _render_template_detail(template_id, api_key, save_history_cb)


def _render_gallery():
    st.markdown("## Pick a story")
    st.caption("Every book is personalized with your child's name — and optionally their photo.")
    templates = get_available_templates()
    if not templates:
        st.warning("No templates available right now. Please check back soon.")
        return
    cols_per_row = 3
    for row_start in range(0, len(templates), cols_per_row):
        cols = st.columns(cols_per_row)
        for i, col in enumerate(cols):
            idx = row_start + i
            if idx >= len(templates):
                continue
            t = templates[idx]
            with col:
                # Whole card is a link to ?tpl=<id>. Streamlit's iframe sandbox
                # ignores anchor navigation, so the link also targets _top to
                # rewrite the parent URL — render_template_mode then picks
                # the id out of st.query_params on the next run.
                st.markdown(
                    f"""
                    <a class="tpl-card-link" href="?tpl={t['id']}" target="_top">
                      <div class="tpl-card">
                        <img src="{_local_cover_uri(t['id']) or t.get('cover_image','')}" alt="{t['name']}">
                        <div class="tpl-card-body">
                          <h4>{t['name']}</h4>
                          <p>{t.get('description','').replace('{name}', 'your child')}</p>
                          <span class="tpl-price">From ₹{TEMPLATE_BASIC_INR}</span>
                          · {t.get('total_pages', '?')} pages
                        </div>
                      </div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Preview this book", key=f"tpl_pick_{t['id']}",
                             use_container_width=True):
                    _reset_flow()
                    st.session_state.tpl_selected_id = t["id"]
                    st.rerun()


def _render_template_detail(template_id: str, api_key: str,
                            save_history_cb: Optional[Callable]):
    templates = get_available_templates()
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        _reset_flow()
        st.rerun()
        return

    # Returned from Cashfree with a verified payment (set in main.py)
    if st.session_state.get("tpl_payment_confirmed"):
        st.session_state.pop("tpl_payment_confirmed", None)
        form = st.session_state.get("tpl_form", {})
        if form.get("child_name"):
            _build_and_show(
                template_id,
                form["child_name"], form.get("gender", "boy"),
                int(form.get("age", 5)), tier=form.get("tier", "basic"),
                api_key=api_key, photo_b64=form.get("photo_b64"),
                save_history_cb=save_history_cb,
            )
            return

    if st.button("← All stories"):
        _reset_flow()
        st.rerun()

    _cov = _local_cover_uri(template_id)
    if _cov:
        _hc1, _hc2 = st.columns([1, 2])
        with _hc1:
            st.markdown(
                f"<img src='{_cov}' style='width:100%;max-width:240px;border-radius:12px;"
                f"box-shadow:0 14px 30px rgba(42,36,32,.18);'>",
                unsafe_allow_html=True,
            )
        with _hc2:
            st.markdown(f"## {template['name']}")
            st.caption(template.get("description", "").replace("{name}", "your child"))
    else:
        st.markdown(f"## {template['name']}")
        st.caption(template.get("description", "").replace("{name}", "your child"))

    # ---- Free preview: first N pages from pre-rendered assets ----
    pages = get_template_pages(template_id)
    preview_gender = st.session_state.get("tpl_form", {}).get("gender", "boy")
    preview_age = st.session_state.get("tpl_form", {}).get("age", 5)
    with st.expander("📖 Sneak peek", expanded=True):
        prev_cols = st.columns(FREE_PREVIEW_PAGES)
        shown = 0
        for page in pages[:FREE_PREVIEW_PAGES]:
            img = _sample_page_image(
                template_id, page["page_number"], preview_gender, preview_age,
                remote_cover=template.get("cover_image", ""),
            )
            with prev_cols[shown]:
                if img:
                    # Portrait sample illustration from a previously generated book.
                    st.markdown(
                        f"<img class='tpl-peek-img' src='{img}' alt='Sample page' />",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div class='tpl-peek-ph'>"
                        "<span>Illustrated page</span></div>",
                        unsafe_allow_html=True,
                    )
                st.caption(
                    page.get("text_template", "")[:90].replace("{name}", "your child")
                    .replace("{He_She}", "They").replace("{he_she}", "they")
                    .replace("{him_her}", "them").replace("{his_her}", "their") + "…"
                )
            shown += 1
        if len(pages) > FREE_PREVIEW_PAGES:
            st.caption(
                f"🔒 {len(pages) - FREE_PREVIEW_PAGES} more pages unlock after purchase."
            )

    st.divider()

    # ---- Already purchased? ----
    user_id = st.session_state.get("user_id")
    prior = has_purchased_template(user_id, template_id) if user_id else None
    if prior:
        st.success(
            f"You already own this book for **{prior.get('metadata', {}).get('child_name', 'your child')}**."
        )
        if st.button("Open my book", type="primary"):
            meta = prior.get("metadata", {})
            _build_and_show(
                template_id,
                meta.get("child_name", "Child"),
                meta.get("gender", "boy"),
                int(meta.get("age", 5)),
                tier=meta.get("tier", "basic"),
                api_key=api_key,
                photo_b64=None,
                save_history_cb=save_history_cb,
            )
            return
        st.caption("Or order another copy for a different child below.")

    # ---- Pending payment? ----
    if st.session_state.get("tpl_cf_order_id"):
        _render_payment_pending(template_id, api_key, save_history_cb)
        return

    # ---- Customize + buy form ----
    # Admins generate books for free (QA, ops, sample creation) — same
    # bypass the custom-story flow already uses in main.py.
    _cur_email = (
        st.session_state.get("user_email", "")
        or (st.session_state.get("auth_user") or {}).get("email", "")
    )
    try:
        from auth import ADMIN_EMAILS as _ADMIN_EMAILS
        _is_admin_tpl = bool(_cur_email) and _cur_email in _ADMIN_EMAILS
    except Exception:
        _is_admin_tpl = False

    st.markdown("### Make it theirs")
    tier = st.radio(
        "Choose your book",
        options=list(TIERS.keys()),
        format_func=lambda k: f"{TIERS[k]['label']} — ₹{TIERS[k]['price']}",
        captions=[TIERS[k]["desc"] for k in TIERS],
        key="tpl_tier",
        horizontal=False,
    )

    with st.form("tpl_customize"):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            child_name = st.text_input("Child's name *", placeholder="Aarav")
        with c2:
            gender = st.selectbox("Gender *", ["boy", "girl"])
        with c3:
            age = st.number_input("Age *", min_value=1, max_value=12, value=5)
        if _is_admin_tpl:
            phone = ""  # phone is only needed for the payment receipt
            st.caption("Signed in as admin — generation is free, no payment needed.")
        else:
            phone = st.text_input(
                "Mobile number * (for payment receipt)", placeholder="10-digit mobile",
                max_chars=10,
            )
        photo_file = None
        if tier == "personalized":
            photo_file = st.file_uploader(
                "Child's photo (clear face, good light)", type=["png", "jpg", "jpeg"]
            )
        if _is_admin_tpl:
            _btn_label = f"Generate book — {TIERS[tier]['label']} (admin, free)"
        else:
            _btn_label = f"Continue to payment — ₹{TIERS[tier]['price']}"
        submitted = st.form_submit_button(
            _btn_label, type="primary", use_container_width=True,
        )

    if submitted:
        if not child_name.strip():
            st.error("Please enter your child's name.")
            return
        if not _is_admin_tpl and not is_valid_phone(phone):
            st.error("Please enter a valid 10-digit mobile number.")
            return
        if tier == "personalized" and photo_file is None:
            st.error("Please upload a photo for the personalized book.")
            return
        photo_b64 = convert_uploaded_file_to_base64(photo_file) if photo_file else None
        st.session_state.tpl_form = {
            "child_name": child_name.strip(),
            "gender": gender,
            "age": int(age),
            "phone": phone,
            "photo_b64": photo_b64,
            "tier": tier,
        }
        # Admin: skip Cashfree and build the book straight away.
        if _is_admin_tpl:
            _build_and_show(
                template_id,
                child_name.strip(), gender, int(age),
                tier=tier, api_key=api_key, photo_b64=photo_b64,
                save_history_cb=save_history_cb,
            )
            return
        result = create_cashfree_order(
            user_id=user_id,
            user_email=st.session_state.get("user_email", ""),
            amount_inr=TIERS[tier]["price"],
            purpose=f"{template['name']} ({TIERS[tier]['label']}) for {child_name.strip()}",
            customer_phone=phone,
            metadata={
                "book_kind": "template",
                "template_id": template_id,
                "tier": tier,
                "child_name": child_name.strip(),
                "gender": gender,
                "age": int(age),
            },
        )
        if not result or result.get("error"):
            st.error((result or {}).get("error", "Could not start payment. Please try again."))
            return
        st.session_state.tpl_cf_order_id = result["order_id"]
        st.session_state.tpl_cf_session = result["payment_session_id"]
        st.rerun()


def _render_payment_pending(template_id: str, api_key: str,
                            save_history_cb: Optional[Callable]):
    """Cashfree Orders-API drop-in checkout (in-page iframe, no Links API)."""
    order_id = st.session_state.get("tpl_cf_order_id")
    session_id = st.session_state.get("tpl_cf_session")
    form = st.session_state.get("tpl_form", {})
    tier = form.get("tier", "basic")
    if not (order_id and session_id):
        _reset_flow(keep_template=True)
        st.rerun()
        return

    st.markdown(
        f"""<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:10px;
        padding:14px 18px;margin-bottom:12px;'>
        <span style='font-size:20px;'>🔒</span>
        <strong style='color:#166534;margin-left:8px;'>
        Secure payment — {TIERS[tier]['label']} · ₹{TIERS[tier]['price']}</strong><br>
        <span style='color:#4b5563;font-size:13px;margin-left:30px;'>
        Complete your payment below. The page updates automatically once done.</span>
        </div>""",
        unsafe_allow_html=True,
    )
    components.html(cashfree_dropin_html(session_id, order_id), height=720, scrolling=False)

    if st.button("✖ Cancel & choose again", key="tpl_pay_cancel"):
        st.session_state.pop("tpl_cf_order_id", None)
        st.session_state.pop("tpl_cf_session", None)
        st.rerun()

    # Always-available manual confirm so a paid user is never stranded.
    st.caption("Finished paying in the window above? Click to continue.")
    if st.button("✅ I've paid — continue", type="primary",
                 use_container_width=True, key="tpl_pay_verify"):
        with st.spinner("Verifying payment…"):
            status = verify_cashfree_order(order_id)
        if status == "PAID":
            confirm_payment_and_credit(order_id, st.session_state.get("user_id"))
            st.session_state.pop("tpl_cf_order_id", None)
            st.session_state.pop("tpl_cf_session", None)
            _build_and_show(
                template_id,
                form.get("child_name", "Child"),
                form.get("gender", "boy"),
                int(form.get("age", 5)),
                tier=tier,
                api_key=api_key,
                photo_b64=form.get("photo_b64"),
                save_history_cb=save_history_cb,
            )
        else:
            st.warning(
                f"Payment not received yet (status: {status}). "
                "If you just paid, wait a few seconds and click again."
            )

def _build_and_show(template_id: str, child_name: str, gender: str, age: int,
                    tier: str, api_key: str, photo_b64: Optional[str],
                    save_history_cb: Optional[Callable]):
    """Assemble the book (instant for basic; re-render for personalized)."""
    with st.spinner("Putting your book together…"):
        book = build_book_from_assets(template_id, child_name, gender, age)
    if not book:
        st.error("Sorry — this template isn't available right now.")
        return

    missing = [p for p in book["pages"] if not p.get("image_url")]
    openrouter_key = st.session_state.get("openrouter_key", "") or st.session_state.get(
        "openrouter_api_key", ""
    )

    # Fill any missing assets live (rare; only if studio pre-render incomplete)
    if missing and api_key:
        from template_book_generator import generate_page_image, compress_image_for_storage
        prog = st.progress(0.0, text="Illustrating a few pages…")
        for i, page in enumerate(missing):
            try:
                img = generate_page_image(api_key, page["image_prompt"], None,
                                          openrouter_key=openrouter_key)
                if img:
                    img = compress_image_for_storage(img)
                    page["image_url"] = img
                    template_store.save_asset(
                        template_id, page["page_number"], gender,
                        template_store._age_to_group(age), img,
                    )
            except Exception:
                pass
            prog.progress((i + 1) / len(missing))
        prog.empty()

    if tier == "personalized" and photo_b64 and api_key:
        prog = st.progress(0.0, text="Illustrating your child into the story…")
        book = personalize_book_with_photo(
            book, api_key, photo_b64, openrouter_key=openrouter_key,
            progress_cb=lambda msg, frac: prog.progress(min(frac, 1.0), text=msg),
        )
        prog.empty()

    st.session_state.tpl_book_data = book
    # Purchase verified — unlock the legacy preview's payment gate
    st.session_state.current_book_payment_status = "paid"
    if save_history_cb:
        try:
            save_history_cb(book)
        except Exception as e:
            logger.warning(f"History save failed: {e}")
    st.balloons()
    st.rerun()


def _render_finished_book(api_key: str, save_history_cb: Optional[Callable]):
    book = st.session_state.tpl_book_data
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← All stories"):
            _reset_flow()
            st.rerun()
    st.success(f"🎉 **{book.get('child_name','')}**'s book is ready!")
    display_template_book_preview(book, api_key=api_key)


# ---------------------------------------------------------------------------
# Admin: Template Studio
# ---------------------------------------------------------------------------

def render_template_studio(api_key: str):
    """Admin tool: pre-render template assets once, monitor coverage.

    Admin-only. The coverage table and per-page status icons are not
    something we ever want a paying customer to see.
    """
    # Defence in depth: even if someone flips show_template_studio in
    # session_state, only an authenticated admin can render this page.
    try:
        from auth import ADMIN_EMAILS
        _email = (st.session_state.get("auth_user") or {}).get("email", "") \
                 or st.session_state.get("user_email", "")
        if _email not in ADMIN_EMAILS:
            st.error("This page is for admins only.")
            return
    except Exception:
        st.error("This page is for admins only.")
        return
    st.markdown("## 🎨 Template Studio")
    st.caption(
        "Pre-render every template page once per gender/age variant. "
        "Customers then get instant books at zero generation cost."
    )

    diag = cashfree_diagnostics()
    with st.expander("💳 Payment gateway health"):
        for k, v in diag.items():
            st.write(f"**{k}:** {v}")

    templates = get_available_templates()

    # ---- Global overview: which templates have ANY images rendered ----
    st.markdown("#### All templates — pre-render status")
    overview_rows = []
    incomplete_ids = []
    for t in templates:
        t_id = t["id"]
        t_pages = get_template_pages(t_id)
        t_status = asset_status(t_id)
        total_pages = len(t_pages)
        pages_with_any = sum(1 for pg in t_pages if t_status.get(pg["page_number"]))
        pct = int(round(100 * pages_with_any / total_pages)) if total_pages else 0
        first_done = "✅" if t_pages and t_status.get(t_pages[0]["page_number"]) else "—"
        if pages_with_any < total_pages:
            incomplete_ids.append(t["name"])
        overview_rows.append({
            "Template": t["name"],
            "Pages": total_pages,
            "Pages w/ image": pages_with_any,
            "% rendered": f"{pct}%",
            "First page": first_done,
            "Status": "✅ complete" if pages_with_any == total_pages and total_pages > 0
                       else ("⏳ partial" if pages_with_any > 0 else "❌ none"),
        })
    st.dataframe(overview_rows, use_container_width=True, hide_index=True)
    if incomplete_ids:
        st.warning(
            "Templates missing one or more images: "
            + ", ".join(incomplete_ids)
            + ". Pick one below and click Pre-render assets to fill it in."
        )
    else:
        st.success("Every template has at least one rendered variant for every page.")

    st.divider()

    template = st.selectbox(
        "Template", templates,
        format_func=lambda t: f"{t['name']} ({t.get('total_pages','?')} pages)",
    )
    if not template:
        return
    template_id = template["id"]

    # Coverage matrix
    pages = get_template_pages(template_id)
    status = asset_status(template_id)
    st.markdown("#### Coverage")
    rows = []
    for gender in GENDERS:
        for group in AGE_GROUPS:
            vk = f"{gender}_{group}"
            done = sum(1 for p in pages if vk in status.get(p["page_number"], []))
            rows.append({"Variant": vk, "Rendered": f"{done}/{len(pages)}",
                         "Complete": "✅" if done == len(pages) else "⏳"})
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("#### Generate")
    c1, c2 = st.columns(2)
    with c1:
        sel_genders = st.multiselect("Genders", GENDERS, default=GENDERS)
    with c2:
        sel_groups = st.multiselect("Age groups", AGE_GROUPS, default=["4-6"])
    overwrite = st.checkbox("Overwrite existing assets", value=False)

    if st.button("🚀 Pre-render assets", type="primary"):
        if not api_key:
            st.error("Configure a Gemini API key first (sidebar).")
            return
        openrouter_key = st.session_state.get("openrouter_key", "") or st.session_state.get(
            "openrouter_api_key", ""
        )
        prog = st.progress(0.0, text="Starting…")
        result = generate_assets_for_template(
            template_id, api_key, openrouter_key=openrouter_key,
            genders=sel_genders, age_groups=sel_groups, overwrite=overwrite,
            progress_cb=lambda msg, frac: prog.progress(min(frac, 1.0), text=msg),
        )
        prog.empty()
        if result.get("error"):
            st.error(result["error"])
        else:
            st.success(
                f"Rendered {result['rendered']} images "
                f"({result['failed']} failed, {result['total_jobs']} queued)."
            )
            st.rerun()
