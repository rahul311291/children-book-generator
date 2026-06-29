"""
Pre-rendered template assets — "create once, sell many".

Each template page image is generated ONCE per (gender, age-group) variant
and stored in Mongo (`template_assets`, one doc per template page with a
`variants` map). Customer purchases then assemble a book instantly from
these assets — no per-customer image generation cost for the basic tier.

The personalized tier re-renders pages with the child's photo as a
reference image, falling back to the pre-rendered asset on any failure.
"""

import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from mongo_client import template_assets_col
from template_data import personalize_template_text, personalize_template_image_prompt
from template_book_generator import (
    get_available_templates,
    get_template_pages,
    generate_page_image,
    compress_image_for_storage,
    _age_to_group,
)

logger = logging.getLogger(__name__)

AGE_GROUPS = ["2-4", "4-6", "6-8", "8-12"]
GENDERS = ["boy", "girl"]

# Neutral names used only while pre-rendering (names rarely appear in images)
_NEUTRAL_NAME = {"boy": "Aarav", "girl": "Aanya"}
# Representative age per group, used in image prompts
_GROUP_AGE = {"2-4": 3, "4-6": 5, "6-8": 7, "8-12": 9}


def variant_key(gender: str, age: int) -> str:
    return f"{gender.lower()}_{_age_to_group(age)}"


def _vkey(gender: str, age_group: str) -> str:
    return f"{gender.lower()}_{age_group}"


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------

def get_asset(template_id: str, page_number: int, gender: str, age: int) -> Optional[str]:
    """Return the pre-rendered image data-URL for a page variant, or None."""
    try:
        doc = template_assets_col().find_one(
            {"template_id": template_id, "page_number": page_number},
            {"variants": 1},
        )
        if not doc:
            return None
        variants = doc.get("variants") or {}
        # Prefer the exact (gender, age) variant; otherwise show ANY rendered
        # variant so the sneak-peek still works regardless of which variant
        # was pre-rendered in Template Studio.
        exact = variants.get(variant_key(gender, age))
        if exact:
            return exact
        return next((v for v in variants.values() if v), None)
    except Exception as e:
        logger.warning(f"get_asset failed: {e}")
        return None


def save_asset(
    template_id: str, page_number: int, gender: str, age_group: str, image_data_url: str
) -> None:
    try:
        template_assets_col().update_one(
            {"template_id": template_id, "page_number": page_number},
            {
                "$set": {
                    f"variants.{_vkey(gender, age_group)}": image_data_url,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )
    except Exception as e:
        logger.error(f"save_asset failed: {e}")


def asset_status(template_id: str) -> Dict[int, List[str]]:
    """Map page_number -> list of variant keys already rendered."""
    status: Dict[int, List[str]] = {}
    try:
        for doc in template_assets_col().find(
            {"template_id": template_id}, {"page_number": 1, "variants": 1}
        ):
            status[doc["page_number"]] = sorted((doc.get("variants") or {}).keys())
    except Exception as e:
        logger.warning(f"asset_status failed: {e}")
    return status


def template_coverage(template_id: str, gender: str, age: int) -> tuple:
    """(rendered_pages, total_pages) for one variant of a template."""
    pages = get_template_pages(template_id)
    vk = variant_key(gender, age)
    status = asset_status(template_id)
    done = sum(1 for p in pages if vk in status.get(p["page_number"], []))
    return done, len(pages)


# ---------------------------------------------------------------------------
# Admin: pre-render assets
# ---------------------------------------------------------------------------

def generate_assets_for_template(
    template_id: str,
    api_key: str,
    openrouter_key: str = "",
    genders: Optional[List[str]] = None,
    age_groups: Optional[List[str]] = None,
    overwrite: bool = False,
    progress_cb: Optional[Callable[[str, float], None]] = None,
) -> dict:
    """Render every missing page/variant for a template. Returns counts."""
    genders = genders or GENDERS
    age_groups = age_groups or AGE_GROUPS
    pages = get_template_pages(template_id)
    if not pages:
        return {"error": f"Template {template_id} not found", "rendered": 0}

    status = asset_status(template_id)
    jobs = []
    for page in pages:
        existing = status.get(page["page_number"], [])
        for gender in genders:
            for group in age_groups:
                if overwrite or _vkey(gender, group) not in existing:
                    jobs.append((page, gender, group))

    rendered, failed = 0, 0
    total = len(jobs)
    for i, (page, gender, group) in enumerate(jobs):
        name = _NEUTRAL_NAME.get(gender, "Aarav")
        age = _GROUP_AGE.get(group, 5)
        prompt = personalize_template_image_prompt(
            page["image_prompt_template"], name, gender, age
        )
        if progress_cb:
            progress_cb(
                f"Page {page['page_number']} — {gender}, age {group}", i / max(total, 1)
            )
        try:
            image_url = generate_page_image(api_key, prompt, None, openrouter_key=openrouter_key)
            if image_url:
                save_asset(
                    template_id,
                    page["page_number"],
                    gender,
                    group,
                    compress_image_for_storage(image_url),
                )
                rendered += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Asset render failed (p{page['page_number']} {gender} {group}): {e}")
            failed += 1
    if progress_cb:
        progress_cb("Done", 1.0)
    return {"rendered": rendered, "failed": failed, "skipped": total - rendered - failed,
            "total_jobs": total}


# ---------------------------------------------------------------------------
# Customer: assemble books
# ---------------------------------------------------------------------------

def build_book_from_assets(
    template_id: str, child_name: str, gender: str, age: int
) -> Optional[dict]:
    """Instantly assemble a personalized book from pre-rendered assets.

    Text is personalized with the child's name; images come from the asset
    store. Returns None if the template has no pages. Pages missing an asset
    get image_url=None (caller may regenerate them live).
    """
    pages = get_template_pages(template_id)
    if not pages:
        return None
    template = next(
        (t for t in get_available_templates() if t["id"] == template_id), {}
    )
    book_pages = []
    for page in pages:
        # Templates that ship a real photo (e.g. Legends — Wikipedia Commons
        # portraits) skip the AI asset lookup entirely. This makes the page
        # show the actual person instead of a random AI-generated face, and
        # avoids the cost of pre-rendering for those pages.
        static_url = page.get("static_image_url")
        if static_url:
            page_image_url = static_url
        else:
            page_image_url = get_asset(
                template_id, page["page_number"], gender, age
            )
        book_pages.append(
            {
                "page_number": page["page_number"],
                "profession_title": personalize_template_text(
                    page.get("profession_title", ""), child_name, gender
                ),
                "text": personalize_template_text(
                    page["text_template"], child_name, gender
                ),
                "image_prompt": personalize_template_image_prompt(
                    page["image_prompt_template"], child_name, gender, age
                ),
                "image_url": page_image_url,
                "image_credit": page.get("image_credit", ""),
                "static_image_url": static_url or "",
            }
        )
    return {
        "template_id": template_id,
        "template_name": template.get("name", "Storybook"),
        "cover_image": template.get("cover_image", ""),
        "child_name": child_name,
        "gender": gender,
        "age": age,
        "pages": book_pages,
        "from_assets": True,
    }


def personalize_book_with_photo(
    book_data: dict,
    api_key: str,
    reference_image_base64: str,
    openrouter_key: str = "",
    progress_cb: Optional[Callable[[str, float], None]] = None,
) -> dict:
    """Re-render every page with the child's photo as reference.

    Falls back to the pre-rendered asset image when generation fails, so the
    customer always gets a complete book.
    """
    pages = book_data.get("pages", [])
    total = len(pages)
    for i, page in enumerate(pages):
        if progress_cb:
            progress_cb(f"Illustrating page {i + 1} of {total}…", i / max(total, 1))
        # Pages backed by a real photo (Wikipedia portraits) skip the photo
        # personalisation — the legend image stays as the real person.
        if page.get("static_image_url"):
            continue
        try:
            new_url = generate_page_image(
                api_key,
                page.get("image_prompt", ""),
                reference_image_base64,
                openrouter_key=openrouter_key,
            )
            if new_url:
                page["image_url"] = compress_image_for_storage(new_url)
        except Exception as e:
            logger.warning(f"Photo personalization failed on page {i + 1}: {e}")
    if progress_cb:
        progress_cb("Done", 1.0)
    book_data["reference_image_base64"] = reference_image_base64
    book_data["personalized_with_photo"] = True
    return book_data
