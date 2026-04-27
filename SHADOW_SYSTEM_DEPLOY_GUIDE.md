# ⚔️ Shadow System — Complete Deployment & Meta Connection Guide

> **Target URL:** `https://auto-bot-01.m-numankhan2007.workers.dev`
> **Architecture:** Cloudflare Python Worker + Static Assets (single deployment)
> **Status before this guide:** Frontend intercepts `/webhook` → Meta verification fails

---

## 🧠 Understanding the Architecture First

Before touching anything, read this. It takes 2 minutes and will save you hours.

```
Browser Request → Cloudflare Edge
                      │
                      ├── /webhook  (GET/POST)  → Python Worker (bot logic)
                      ├── /health   (GET)        → Python Worker (health check)
                      └── /*        (everything) → Static React Frontend
```

**The key insight:** A Cloudflare Worker with Assets is a single deployment where ONE Worker script controls ALL routing. The Worker decides: "Is this an API route? Handle it myself. Is this a frontend route? Serve the static file."

**Why it was broken:** Your `wrangler.toml` had no `[assets]` block. The Worker didn't know the frontend existed. And your `main.py` returned `404` instead of serving the React app for non-API routes.

---

## 🔴 PART 1: Fix the Code (3 files)

Apply these changes to your GitHub repo. Cloudflare will auto-deploy.

### Fix 1 of 3 — `backend/worker/wrangler.toml` (REPLACE ENTIRELY)

```toml
# ── wrangler.toml — Shadow System Worker Configuration ──
# This single file controls BOTH the Python Worker AND the React frontend.
# Deploy with: cd backend/worker && pip install uv && uvx --from workers-py pywrangler deploy

name = "auto-bot-01"
main = "main.py"
compatibility_date = "2026-04-26"
compatibility_flags = ["python_workers"]

# ── Static Assets (React Frontend) ──
# This tells Cloudflare: "Also serve these files as static assets."
# The binding = "ASSETS" lets our Python code call self.env.ASSETS.fetch(request)
# to serve the frontend for non-API routes.
[assets]
directory = "../../frontend/dist"
binding = "ASSETS"

# ── Observability ──
[observability]
enabled = true

# ── Secrets (set via CLI or dashboard — NEVER put values here) ──
# wrangler secret put GEMINI_KEY
# wrangler secret put INSTA_TOKEN
# wrangler secret put APP_SECRET
# wrangler secret put VERIFY_TOKEN
# wrangler secret put INSTAGRAM_ACCOUNT_ID
# wrangler secret put BOT_USERNAME
```

> **Critical:** The `name` must match your existing Worker in the dashboard (`auto-bot-01`). Your old `wrangler.toml` said `name = "shadow-bot"` which would have created a *second*, separate Worker.

---

### Fix 2 of 3 — `backend/worker/main.py` (ONE LINE CHANGE)

Find the section at the bottom of the `fetch` method that says:

```python
# ── 404 ──
return Response("Not Found", status=404)
```

**Replace it with:**

```python
# ── Serve React Frontend (for all non-API routes) ──
# env.ASSETS.fetch() passes the request to Cloudflare's asset server,
# which serves the built React files from frontend/dist.
# This is what makes the portfolio website visible at the root URL.
return await self.env.ASSETS.fetch(request)
```

That is the **only** change needed in `main.py`. Everything else — the webhook handler, Gemini calls, Pollinations — is already correct.

---

### Fix 3 of 3 — DELETE `frontend/public/_routes.json`

Delete this file entirely. It is a **Cloudflare Pages** concept and does nothing in a Cloudflare Worker deployment. Its presence is confusing and irrelevant.

```bash
# In your repo, simply delete:
frontend/public/_routes.json
```

---

## 🟠 PART 2: Fix the Cloudflare Dashboard Settings

Go to your Worker dashboard → **Settings** tab → **Build** section. Update:

| Field | Current (Wrong) | Correct |
|---|---|---|
| Build command | `cd frontend && npm install && npm run build` | `cd frontend && npm install && npm run build` ✅ (keep this) |
| Deploy command | `cd backend/worker && npx wrangler deploy` | `cd backend/worker && pip install uv && uvx --from workers-py pywrangler deploy` |
| Root directory | `/` | `/` ✅ (keep this) |

**Why `pywrangler` instead of `wrangler`:** Raw `wrangler deploy` does NOT bundle Python dependencies. It uploads only your `.py` files, so the `workers` module is missing at runtime (Error 10021). `pywrangler` reads your `pyproject.toml`, bundles `workers-py` and all dependencies, then deploys the complete package.

---

## 🔐 PART 3: Set All Secrets in Cloudflare

Your dashboard currently only shows `VERIFY_TOKEN` as a Variable. The remaining five secrets are missing. The Worker will crash silently without them.

### Option A — Cloudflare Dashboard (Easiest)

Go to your Worker → **Settings** → **Variables and Secrets** → click **+ Add**

For each secret below, set **Type = Secret** (not Variable):

| Secret Name | Where to Get the Value |
|---|---|
| `VERIFY_TOKEN` | Already set. Change type to Secret. Value: `shadow_system_bot` |
| `APP_SECRET` | Meta App Dashboard → Settings → Basic → "App Secret" (click Show) |
| `INSTA_TOKEN` | Your long-lived Instagram Page Access Token (see Part 4 below) |
| `INSTAGRAM_ACCOUNT_ID` | Graph API Explorer → GET `/me` → copy the `id` field |
| `BOT_USERNAME` | Your bot's Instagram username WITHOUT the @ symbol |
| `GEMINI_KEY` | Google AI Studio → https://aistudio.google.com/app/apikeys |

> **Important:** The token secret is named `INSTA_TOKEN` in your Worker code (`self.env.INSTA_TOKEN`), not `PAGE_ACCESS_TOKEN`. Use exactly `INSTA_TOKEN` as the name.

### Option B — Wrangler CLI (More Secure)

```bash
cd backend/worker

npx wrangler secret put VERIFY_TOKEN
# Enter: shadow_system_bot

npx wrangler secret put APP_SECRET
# Enter: (paste your Meta App Secret)

npx wrangler secret put INSTA_TOKEN
# Enter: (paste your long-lived token)

npx wrangler secret put INSTAGRAM_ACCOUNT_ID
# Enter: (paste your IG account ID)

npx wrangler secret put BOT_USERNAME
# Enter: (your bot's username without @)

npx wrangler secret put GEMINI_KEY
# Enter: (paste your new Gemini key)
```

---

## 🔵 PART 4: Get Your Instagram Long-Lived Token (`INSTA_TOKEN`)

This is the token that lets your bot send messages. It expires every 60 days (the auto-refresh in `token_refresh.py` handles renewal, but for the initial setup you must get it manually).

### Step 1 — Get a Short-Lived Token

1. Go to **https://developers.facebook.com/tools/explorer/**
2. At the top-right, select your App: **SHADOW-SYSTEM-IG**
3. Under "User or Page", select your **Instagram Business/Creator Page**
4. Add these permissions by clicking them in the left panel:
   - `instagram_business_basic`
   - `instagram_business_manage_messages`
   - `pages_messaging`
5. Click **Generate Access Token**
6. Copy the token — this is your short-lived token (expires in ~1 hour)

### Step 2 — Exchange for a Long-Lived Token (60 days)

Run this in your terminal (replace the placeholders):

```bash
curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=YOUR_APP_ID
  &client_secret=YOUR_APP_SECRET
  &fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

The response will look like:
```json
{
  "access_token": "EAAxxxxxxxx...",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

Copy the `access_token` value. This is your `INSTA_TOKEN`.

### Step 3 — Get Your Instagram Account ID

```bash
curl "https://graph.facebook.com/v19.0/me?fields=id,name&access_token=YOUR_LONG_LIVED_TOKEN"
```

The `id` field in the response is your `INSTAGRAM_ACCOUNT_ID`.

---

## 🟢 PART 5: Connect Meta Webhook to Your Worker

This is the step that makes Meta send events to your bot.

### Step 1 — Navigate to Webhooks

1. Go to **https://developers.facebook.com/apps/**
2. Select **SHADOW-SYSTEM-IG**
3. Left sidebar → **Use cases** → Click on your Instagram use case
4. Click **"API setup with Instagram login"** or **Webhooks** in the sidebar

### Step 2 — Configure the Callback

Click **"Add Webhook"** or **"Edit"** on the existing webhook:

| Field | Value |
|---|---|
| **Callback URL** | `https://auto-bot-01.m-numankhan2007.workers.dev/webhook` |
| **Verify Token** | `shadow_system_bot` |

Click **Verify and Save**. Meta will send a GET request to your Worker. If the code changes from Part 1 are deployed, the Worker will respond with the challenge and verification will succeed.

> **If verification fails:** Check that `VERIFY_TOKEN` is set correctly in Cloudflare secrets and that the deployment went through. Test manually: `https://auto-bot-01.m-numankhan2007.workers.dev/webhook?hub.mode=subscribe&hub.verify_token=shadow_system_bot&hub.challenge=TEST` — you should see `TEST` as plain text.

### Step 3 — Subscribe to Webhook Fields

After verification, you will see a list of subscribable fields. Enable:

- ✅ `messages` — receives all DMs and group messages (required for bot commands)
- ✅ `messaging_postbacks` — receives button taps
- ✅ (Optional) `message_reads` — read receipts

### Step 4 — Subscribe Your Instagram Account

On the webhook configuration page, find the section **"Subscribed objects"** and add your Instagram account. This links your specific account to the webhook subscription.

---

## 🧪 PART 6: Verify Everything is Working

Run these tests in order.

### Test 1 — Worker is alive
```
GET https://auto-bot-01.m-numankhan2007.workers.dev/health
Expected: {"status":"alive","service":"shadow-system-bot","version":"3.0.0-cf"}
```

### Test 2 — Frontend is served
```
GET https://auto-bot-01.m-numankhan2007.workers.dev/
Expected: Your Shadow System React portfolio page loads
```

### Test 3 — Webhook verification passes
```
GET https://auto-bot-01.m-numankhan2007.workers.dev/webhook?hub.mode=subscribe&hub.verify_token=shadow_system_bot&hub.challenge=MONARCH
Expected: MONARCH (plain text, no quotes, no JSON)
```

### Test 4 — Meta verification in dashboard
In Meta App Dashboard → Webhooks → click **Test** next to your webhook.
Expected: Green checkmark ✅

### Test 5 — Bot responds to commands
In your Instagram group chat, send:
```
/ask What is the Shadow System?
```
Expected: A response from the bot in the Shadow System persona.

---

## 🗂 PART 7: Final Project Structure (For Reference)

After all changes, your repo should look like this:

```
AUTO-BOT/
├── .gitignore
├── LICENSE
├── README.md
│
├── backend/
│   ├── ai_engine.py          ← FastAPI version (local dev only)
│   ├── bot.py
│   ├── command_router.py
│   ├── config.py
│   ├── cooldown.py
│   ├── main.py
│   ├── requirements.txt
│   ├── token_refresh.py
│   └── worker/
│       ├── main.py           ← ✅ FIXED: ASSETS fallthrough
│       ├── pyproject.toml
│       └── wrangler.toml     ← ✅ FIXED: [assets] block + correct name
│
└── frontend/
    ├── public/
    │   └── (no _routes.json) ← ✅ DELETED
    ├── src/
    │   └── ...
    ├── package.json
    └── vite.config.js
```

---

## ⚠️ Common Mistakes and Solutions

**"Verification failed" from Meta:**
→ Check that `VERIFY_TOKEN` in Cloudflare secrets matches exactly what you entered in the Meta dashboard. No spaces, no quotes.

**"Not Found" when visiting the Worker URL:**
→ The `[assets]` block or the `ASSETS.fetch()` fallthrough is not deployed yet. Trigger a new deployment.

**"Invalid signature" on POST events:**
→ `APP_SECRET` in Cloudflare secrets does not match the App Secret in Meta App Dashboard → Settings → Basic.

**Bot sends welcome but doesn't respond to `/ask`:**
→ `GEMINI_KEY` is missing or expired. Regenerate at aistudio.google.com and update the secret.

**Deployment fails with "wrangler.toml not found":**
→ The deploy command in Cloudflare dashboard must start with `cd backend/worker &&`.

**Deployment fails with "ModuleNotFoundError: No module named 'workers'":**
→ You are using raw `npx wrangler deploy` instead of `pywrangler`. Change the deploy command to: `cd backend/worker && pip install uv && uvx --from workers-py pywrangler deploy`. Also ensure `pyproject.toml` has `[dependency-groups] dev = ["workers-py", "workers-runtime-sdk"]` and `wrangler.toml` does NOT have `disable_python_external_sdk` in compatibility_flags.

**Frontend shows blank page:**
→ The frontend was not built before deployment. Ensure Build command runs `cd frontend && npm install && npm run build` before the deploy command.

---

## 🔄 Maintenance — Token Refresh (Every 60 Days)

Your long-lived Instagram token expires in 60 days. To refresh it:

```bash
curl "https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=YOUR_APP_ID
  &client_secret=YOUR_APP_SECRET
  &fb_exchange_token=YOUR_CURRENT_INSTA_TOKEN"
```

Then update the secret in Cloudflare:
```bash
cd backend/worker && npx wrangler secret put INSTA_TOKEN
# Paste the new token
```

> The `token_refresh.py` in `backend/` handles this automatically for the local FastAPI version, but Cloudflare Workers don't support persistent background tasks. You must refresh manually every 60 days (or set a calendar reminder).

---

*Shadow System v3.0.0-cf · Cloudflare Python Workers · Meta Graph API v19.0*
