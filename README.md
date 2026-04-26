# ⚔️ Shadow System — Instagram Automation Bot

> Monarch-level engineering prompt showcase + production-ready Instagram group chat webhook bot.
> Deployed on **Cloudflare** (Pages + Python Worker) — fully serverless, no credit card required.

## 📁 Monorepo Structure

```
INSTAGRAM-BOT/
├── frontend/               # React 19 + Vite 8 — Prompt showcase UI (Cloudflare Pages)
│   ├── src/
│   │   ├── components/     # BackgroundEffects, BootScreen, Header, Sidebar,
│   │   │                   # PromptPanel, UsageGuide, Footer, ErrorBoundary, CopyToast
│   │   ├── hooks/          # useInView, useTypewriter, useCountUp, useMouseGlow, useKeyboardShortcut
│   │   ├── data/           # prompt.js — PROMPT, SECTIONS, STATS, USAGE_STEPS
│   │   └── App.jsx         # Main application with ErrorBoundary wrapping
│   ├── index.html          # Entry point with OG/Twitter meta tags
│   ├── vite.config.js      # Build optimizations with manual chunk splitting
│   └── package.json
│
├── backend/
│   ├── worker/             # Cloudflare Python Worker — Production deployment
│   │   ├── main.py         # Worker entrypoint (webhook handler + AI engine)
│   │   ├── wrangler.toml   # Worker configuration
│   │   ├── pyproject.toml  # Python project metadata
│   │   └── .dev.vars       # Local dev secrets (gitignored)
│   │
│   ├── main.py             # FastAPI app (local development only)
│   ├── config.py           # Env loading with loud failure on missing vars
│   ├── bot.py              # Webhook parser + welcome message sender
│   ├── ai_engine.py        # Gemini + Pollinations AI engine
│   ├── command_router.py   # Message parser + command classifier
│   ├── cooldown.py         # Per-user rate limiter
│   ├── token_refresh.py    # Long-lived token exchange + auto-refresh
│   ├── requirements.txt    # Pinned dependencies (local dev)
│   └── .env.example        # Template with setup instructions
│
├── .gitignore              # Covers frontend/, backend/, and worker secrets
└── README.md               # This file
```

---

## 🚀 Deployment (Cloudflare — Production)

### Frontend → Cloudflare Pages

**Option A: Git Integration (Recommended)**
1. Push this repo to GitHub/GitLab
2. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) → Workers & Pages → Create
3. Connect your repository
4. Set these build settings:

| Setting | Value |
|---------|-------|
| **Root directory** | `frontend` |
| **Build command** | `npm run build` |
| **Build output directory** | `dist` |

> ⚠️ Setting **Root directory** to `frontend` fixes the `ENOENT: Could not read package.json` error.

**Option B: Manual Deploy**
```bash
cd frontend
npm install && npm run build
npx wrangler pages deploy dist --project-name=shadow-system
```

### Backend → Cloudflare Python Worker

```bash
cd backend/worker

# Set production secrets (prompted for values)
npx wrangler secret put GEMINI_KEY
npx wrangler secret put INSTA_TOKEN
npx wrangler secret put APP_SECRET
npx wrangler secret put VERIFY_TOKEN
npx wrangler secret put INSTAGRAM_ACCOUNT_ID
npx wrangler secret put BOT_USERNAME

# Deploy
uvx --from workers-py pywrangler deploy
```

Your webhook URL will be: `https://shadow-bot.<your-subdomain>.workers.dev/webhook`

---

## 🛠️ Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
# → Opens at http://localhost:5173
```

### Backend (FastAPI — for local testing)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn main:app --reload --port 8000
```

### Backend (Cloudflare Worker — local emulation)

```bash
cd backend/worker
# Edit .dev.vars with your secrets
uvx --from workers-py pywrangler dev
# → Runs at http://localhost:8787
```

---

## 🔗 Meta Webhook Setup

1. **Get Page Access Token** — [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. **Register Webhook** — Meta App Dashboard → Webhooks → Add Subscription
   - **Callback URL**: `https://shadow-bot.<your-subdomain>.workers.dev/webhook`
   - **Verify Token**: Same as your `VERIFY_TOKEN` secret
3. **Subscribe to Events**: `messages`, `messaging_postbacks`
4. **Make Bot Admin** in the Instagram group chat

---

## ⚠️ Known Gotchas

| Issue | Solution |
|-------|----------|
| **`ENOENT: Could not read package.json`** | Set Pages Root directory to `frontend` |
| **Bot is not admin** | 403 error — add bot as admin in group chat settings |
| **Duplicate events** | Meta sends at-least-once — acceptable for welcome messages |
| **Token expired** | Run `token_refresh.py` locally every 50 days, or use a System User token |
| **Cold starts** | First request after idle may take ~1-2s. Subsequent requests are instant |

---

## 🛡️ Security

- **HMAC-SHA256** signature verification on every webhook POST
- **Cloudflare Secrets** for all credentials (never in code or wrangler.toml)
- **`.dev.vars`** for local development (gitignored)
- **XSS eliminated** from frontend (no `dangerouslySetInnerHTML`)
- **ErrorBoundary** prevents full app crashes

---

## 📊 Tech Stack

| Layer | Technology | Deployment |
|-------|-----------|------------|
| Frontend | React 19 + Vite 8 | Cloudflare Pages |
| Backend | Python Worker | Cloudflare Workers |
| AI Text | Gemini 2.0 Flash | REST API |
| AI Image | Pollinations.ai | URL construction |
| API | Meta Graph API v19.0 | Webhook integration |

---

*Built with the Shadow System protocol. Arise, Hunter.* ⚔️
