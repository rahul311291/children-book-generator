# Maintenance scripts

One-off scripts that talk to the Atlas cluster the Streamlit app uses. They
don't import any app modules — they only need `pymongo`. Connection details
default to the production cluster; override with `MONGODB_URI` and
`MONGODB_DB` env vars if needed.

## audit_template_assets.py

Reads `template_assets` and prints a per-template coverage report:
total pages, pages with any image, % of variants rendered, whether page 1
is rendered (the first sneak-peek slot), and any pages missing entirely.
Read-only — never deletes or writes.

    pip install pymongo
    python scripts/audit_template_assets.py

Tip: the same coverage shows in-app at the top of Template Studio after
the latest deploy.

## cleanup_old_templates.py

Purges every Mongo trace of templates we removed from the storefront
(currently Snow White `a2222222-…` and Cricket Champion `a3333333-…`).
Wipes from `template_assets`, `image_pool`, `book_cache`, `purchases`,
and `book_history` (matches `template_id` at top level and nested under
`metadata` / `story_data`).

Always dry-run first:

    pip install pymongo
    python scripts/cleanup_old_templates.py             # shows counts
    python scripts/cleanup_old_templates.py --apply     # actually deletes

To add another id to the purge list later, edit the `REMOVED_TEMPLATES`
list at the top of the script.

## Where to run them

You don't need a local clone. Pick whatever's easiest:

1. **Render shell.** Render dashboard → your service → Shell tab. You're
   already in the repo root and the venv. `pip install pymongo` (if not
   already), then run as above.
2. **Atlas Data Explorer.** No Python at all. cloud.mongodb.com → Browse
   Collections → filter by `{ "template_id": "<id>" }` → delete. Repeat
   for each collection.
3. **Local clone.** `git clone …`, `pip install pymongo`, run.
