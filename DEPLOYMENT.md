# Deployment checklist (Streamlit Cloud)

## 1. MongoDB Atlas
- Create a free/shared cluster, a database user, and allow access from `0.0.0.0/0` (Streamlit Cloud has no fixed IP).
- Set `MONGODB_URI` and `MONGODB_DB` in secrets. Indexes are created automatically on first run.

## 2. Cashfree (the #1 source of "payment not going through")
- Get **production** App ID + Secret from the Cashfree merchant dashboard (Developers → API Keys).
- In secrets set:
  ```toml
  CASHFREE_APP_ID = "prod app id"
  CASHFREE_SECRET_KEY = "prod secret"
  CASHFREE_ENV = "production"        # MUST be "production" with production keys
  APP_BASE_URL = "https://your-app.streamlit.app"
  ```
- ⚠️ Production keys with `CASHFREE_ENV="sandbox"` (or vice-versa) cause `401 authentication failed` — this was the original bug. The admin sidebar → **💳 Payments health** shows the active environment.
- Payment links require a real 10-digit customer phone — the app now collects it at checkout.
- `APP_BASE_URL` powers the post-payment redirect (`?cf_link_id=...`) that auto-unlocks the book.

## 3. Email OTP (SMTP)
- Gmail: enable 2FA, create an App Password, set `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`.
- Keep `ALLOW_DEV_OTP = "false"` in production. Setting it to `"true"` prints the OTP on screen when SMTP fails — dev only.

## 4. Google sign-in (optional but recommended)
- Google Cloud Console → APIs & Services → Credentials → **OAuth client ID** (Web application).
- Authorized redirect URI: `https://your-app.streamlit.app/oauth2callback`
- Fill the `[auth]` block in secrets (`client_id`, `client_secret`, random `cookie_secret`, `redirect_uri`).
- Requires `streamlit>=1.44` + `Authlib` (already in requirements.txt). If `[auth]` is absent the button simply doesn't render — email OTP still works.

## 5. AI generation keys (admin account)
- Sign in with the admin email (`ADMIN_EMAILS` in `auth.py`), open the sidebar, and save your Gemini API key (and optionally OpenRouter / Vertex AI service-account JSON).
- These are stored on the admin user in Mongo and **shared automatically with customers** as the generation backend.

## 6. Pre-render template assets (do this before launch)
- Sidebar → **🎨 Template Studio** → pick a template → select genders/age groups → **Pre-render assets**.
- Start with `4-6` boy+girl for every template, then expand. Customers buying the basic tier get instant books only for variants you've rendered (missing pages fall back to live generation).

## 7. Smoke test
1. Incognito window → sign in with a non-admin email (OTP).
2. Buy a template book with a ₹149 production payment (refund yourself after).
3. Confirm the redirect back unlocks the book, it appears under **My Books**, and the PDF downloads.
