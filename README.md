# 📚 Storytime Studio

Personalized children's storybooks, sold direct to parents. Built with Streamlit, MongoDB, Gemini/Vertex AI image generation, and Cashfree payments.

## What customers get

- **Story Library** — pre-rendered template books (e.g. *When I Grow Up*, fairy-tale retellings). Personalized with the child's name on every page. Two tiers:
  - **Digital Book (₹149)** — instant, assembled from pre-rendered assets at zero generation cost
  - **Photo Personalized (₹249)** — upload a photo; every page is re-illustrated with the child as the hero
- **Custom Story** — fully bespoke AI-generated story and illustrations (₹500 PDF / ₹1100 printed)

## How it works

```
auth.py                  Passwordless sign-in: Google OIDC (st.login) + email OTP
payments.py              Cashfree Payment Links + purchases/entitlements + credits
template_store.py        Pre-rendered template assets ("create once, sell many")
template_flow.py         Customer storefront + admin Template Studio
template_book_generator  Legacy template engine, PDF builder, image generation
main.py                  App shell, routing, custom-story wizard
mongo_client.py          MongoDB collections + indexes
```

### Pre-rendered assets
Template page images are generated **once** per (gender × age-group) variant in the admin **🎨 Template Studio** and stored in Mongo (`template_assets`). Customer purchases assemble books instantly — no per-customer AI cost on the basic tier.

### Payments
Cashfree Payment Links (v2023-08-01). The environment is derived from `CASHFREE_ENV` — **keys and environment must match** (production keys + `CASHFREE_ENV="production"`). Paid links are recorded in `purchases` as permanent entitlements; customers can re-open their books without paying again. The admin sidebar has a **💳 Payments health** panel to diagnose configuration.

### Auth
No passwords. Google sign-in (Streamlit native OIDC, needs `[auth]` in secrets) and/or email one-time codes over SMTP. Sessions persist 7 days via a cookie-backed token.

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in values
streamlit run main.py
```

See **DEPLOYMENT.md** for the full production checklist.
