"""Purge every Mongo trace of templates we removed from the storefront.

Currently removes:
  - Snow White and the Kind-Hearted Child   (id a2222222-…)
  - Cricket Champion - Mastering Every Shot (id a3333333-…)

Run locally once from the project root (where template_book_generator.py
lives — the script doesn't import it, but you'll already have pymongo
installed there):

    pip install pymongo
    python cleanup_old_templates.py             # dry run — shows counts
    python cleanup_old_templates.py --apply     # actually deletes

Override the connection with env vars if you need to point at a different
cluster: MONGODB_URI, MONGODB_DB.
"""

import os
import sys

MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://userClaudecode:nByhfihaa1YupRFp@childrenbooks.saubl0r.mongodb.net/",
)
MONGODB_DB = os.environ.get("MONGODB_DB", "children_book_generator")

REMOVED_TEMPLATES = [
    ("a2222222-2222-2222-2222-222222222222", "Snow White and the Kind-Hearted Child"),
    ("a3333333-3333-3333-3333-333333333333", "Cricket Champion - Mastering Every Shot"),
]


def main(apply: bool) -> None:
    try:
        from pymongo import MongoClient
    except ImportError:
        print("ERROR: pymongo not installed.  pip install pymongo")
        sys.exit(1)

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    db = client[MONGODB_DB]

    print("=" * 72)
    print(f"  Target DB:  {MONGODB_DB}")
    print(f"  Mode:       {'APPLY (will delete)' if apply else 'DRY RUN (read-only)'}")
    print("=" * 72)

    grand_total = 0
    for tid, name in REMOVED_TEMPLATES:
        print(f"\n  Template: {name}")
        print(f"  ID:       {tid}")
        print("-" * 72)

        targets = [
            ("template_assets",  {"template_id": tid}),
            ("image_pool",       {"template_id": tid}),
            ("book_cache",       {"template_id": tid}),
            ("purchases",        {"template_id": tid}),
            # book_history stores the id at top level AND nested
            ("book_history",     {"$or": [
                {"template_id": tid},
                {"metadata.template_id": tid},
                {"story_data.template_id": tid},
            ]}),
        ]

        per_template = 0
        for col_name, query in targets:
            col = db[col_name]
            count = col.count_documents(query)
            print(f"    {col_name:18s} matches: {count}")
            per_template += count
            if apply and count > 0:
                res = col.delete_many(query)
                print(f"                       deleted: {res.deleted_count}")
        grand_total += per_template
        print(f"    Subtotal: {per_template}")

    print()
    print("=" * 72)
    if apply:
        print(f"  TOTAL DELETED across all templates / collections: {grand_total}")
    else:
        print(f"  TOTAL THAT WOULD BE DELETED: {grand_total}")
        print()
        print("  Re-run with `--apply` to actually delete.")
    print("=" * 72)


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    main(apply=apply_flag)
