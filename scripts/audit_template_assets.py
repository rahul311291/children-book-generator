"""Audit which templates have pre-rendered assets in MongoDB.

Run locally from the project root (where template_book_generator.py lives) — it
needs the DEFAULT_TEMPLATES definition. The script does NOT push, write or
modify anything; it only reads template_assets and prints a coverage report.

    cd /path/to/children-book-generator
    pip install pymongo  # if not already installed
    python audit_template_assets.py

Connection details below are the ones you shared in chat. Override via env
vars (MONGODB_URI, MONGODB_DB) if you want to point at a different cluster.
"""

import os
import sys

MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://userClaudecode:nByhfihaa1YupRFp@childrenbooks.saubl0r.mongodb.net/",
)
MONGODB_DB = os.environ.get("MONGODB_DB", "children_book_generator")

# Variants Template Studio uses for the coverage matrix.
GENDERS = ["boy", "girl"]
AGE_GROUPS = ["2-4", "4-6", "6-8", "8-12"]


def _load_templates():
    try:
        from template_book_generator import get_available_templates, get_template_pages
    except Exception as exc:  # pragma: no cover — script-only helper
        print(
            "ERROR: could not import template_book_generator. "
            "Run this script from the repo root.\n  "
            f"{exc}"
        )
        sys.exit(1)
    return get_available_templates(), get_template_pages


def _connect():
    try:
        from pymongo import MongoClient
    except ImportError:
        print("ERROR: pymongo not installed.  pip install pymongo")
        sys.exit(1)
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")  # raise early if creds/network are wrong
    return client[MONGODB_DB]


def main() -> None:
    templates, get_template_pages = _load_templates()
    db = _connect()
    col = db["template_assets"]

    print("=" * 78)
    print(f"  Pre-render coverage for {len(templates)} templates")
    print(f"  Connected to:  {MONGODB_DB}")
    print(f"  Variants checked per page:  {len(GENDERS) * len(AGE_GROUPS)} "
          f"({', '.join(GENDERS)} x {', '.join(AGE_GROUPS)})")
    print("=" * 78)
    print()

    overall_complete = 0
    overall_partial = 0
    overall_none = 0
    incomplete_names: list[str] = []

    for t in templates:
        t_id = t["id"]
        name = t["name"]
        pages = get_template_pages(t_id)
        total_pages = len(pages)

        # Build a {page_number: [variant_keys...]} map for this template
        status: dict[int, list[str]] = {}
        for doc in col.find({"template_id": t_id}, {"page_number": 1, "variants": 1}):
            status[doc["page_number"]] = sorted((doc.get("variants") or {}).keys())

        pages_with_any = sum(1 for pg in pages if status.get(pg["page_number"]))

        # Variant-level coverage (out of total_pages * len(variants))
        all_variants = [f"{g}_{ag}" for g in GENDERS for ag in AGE_GROUPS]
        variant_done = 0
        for pg in pages:
            existing = set(status.get(pg["page_number"], []))
            variant_done += sum(1 for v in all_variants if v in existing)
        variant_total = total_pages * len(all_variants)
        variant_pct = (100 * variant_done / variant_total) if variant_total else 0

        if pages_with_any == 0:
            tag = "EMPTY    "
            overall_none += 1
            incomplete_names.append(name)
        elif pages_with_any == total_pages and variant_done == variant_total:
            tag = "COMPLETE "
            overall_complete += 1
        else:
            tag = "PARTIAL  "
            overall_partial += 1
            incomplete_names.append(name)

        print(f"  [{tag}] {name}")
        print(f"            pages with any image : {pages_with_any} / {total_pages}")
        print(f"            variants rendered    : {variant_done} / {variant_total} "
              f"({variant_pct:.0f}%)")

        # First page is what the sneak peek shows first — flag if missing
        first_pn = pages[0]["page_number"] if pages else None
        first_done = bool(status.get(first_pn)) if first_pn is not None else False
        print(f"            page 1 rendered      : {'yes' if first_done else 'NO — sneak peek shows placeholder'}")

        # Per-page detail when partial
        if 0 < pages_with_any < total_pages:
            missing_pages = [pg["page_number"] for pg in pages
                             if not status.get(pg["page_number"])]
            print(f"            pages missing entirely: {missing_pages}")
        print()

    print("=" * 78)
    print(f"  Summary:  {overall_complete} complete, {overall_partial} partial, "
          f"{overall_none} empty (of {len(templates)} total)")
    if incomplete_names:
        print()
        print("  Templates that need (more) pre-rendering:")
        for n in incomplete_names:
            print(f"    - {n}")
        print()
        print("  How to fill them in:  open the app as admin, click Template Studio,")
        print("  pick each template above, leave 'Overwrite existing assets' OFF,")
        print("  and click '🚀 Pre-render assets'.")
    else:
        print()
        print("  Every template has every variant rendered. Sneak peek will be full.")
    print("=" * 78)


if __name__ == "__main__":
    main()
