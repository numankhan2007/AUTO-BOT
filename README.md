# ⚔️ Shadow System — Instagram Automation Bot

> Monarch-level engineering prompt showcase + production-ready Instagram group chat webhook bot.

## 📁 Monorepo Structure

```
INSTAGRAM-BOT/
├── frontend/           # React 19 + Vite 8 — Prompt showcase UI
│   ├── src/
│   │   ├── components/ # BackgroundEffects, BootScreen, Header, Sidebar,
│   │   │               # PromptPanel, UsageGuide, Footer, ErrorBoundary, CopyToast
│   │   ├── hooks/      # useInView, useTypewriter, useCountUp, useMouseGlow, useKeyboardShortcut
│   │   ├── data/       # prompt.js — PROMPT, SECTIONS, STATS, USAGE_STEPS
│   │   └── App.jsx     # Main application with ErrorBoundary wrapping
│   ├── index.html      # Entry point with OG/Twitter meta tags
│   ├── vite.config.js  # Build optimizations with manual chunk splitting
│   └── package.json
│
├── backend/            # FastAPI + Uvicorn — Instagram webhook server
│   ├── main.py         # FastAPI app, APScheduler lifespan, webhook endpoints
│   ├── config.py       # Env loading with loud failure on missing vars
│   ├── bot.py          # Webhook parser + welcome message sender
│   ├── token_refresh.py# Long-lived token exchange + auto-refresh
│   ├── requirements.txt# Pinned dependencies
│   └── .env.example    # Template with setup instructions
│
├── .gitignore          # Covers both frontend/ and backend/
└── README.md           # This file
```

---

## 🚀 Quick Start

### Frontend (Prompt Showcase UI)

```bash
cd frontend
npm install
npm run dev
# → Opens at http://localhost:5173
```

### Backend (Instagram Webhook Bot)

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Meta API credentials (see .env.example for instructions)

# Start the server
uvicorn main:app --reload --port 8000
# → Runs at http://localhost:8000
```

---

## 🔗 Meta Webhook Setup

### 1. Get Your Page Access Token

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your App → Select your Page
3. Add permissions: `pages_messaging`, `instagram_manage_messages`
4. Click **Generate Access Token** (this is short-lived, ~1 hour)
5. Exchange for long-lived token:
   ```bash
   cd backend && source venv/bin/activate
   python -c "
   import asyncio
   from token_refresh import exchange_for_long_lived_token
   token = asyncio.run(exchange_for_long_lived_token('YOUR_SHORT_TOKEN'))
   print(f'Long-lived token: {token}')
   "
   ```
6. Paste the long-lived token into `backend/.env`

### 2. Start ngrok Tunnel

```bash
ngrok http 8000
# Output shows: Forwarding https://xxxx.ngrok-free.app → http://localhost:8000
```

### 3. Register Webhook in Meta Dashboard

1. Go to [Meta App Dashboard](https://developers.facebook.com/apps/) → Your App
2. Navigate to **Webhooks** → **Add Subscription**
3. **Callback URL**: `https://xxxx.ngrok-free.app/webhook`
4. **Verify Token**: Same string you set in `backend/.env` as `VERIFY_TOKEN`
5. Click **Verify and Save**

### 4. Subscribe to Events

1. In the Webhooks panel, find **Instagram** or **Page**
2. Subscribe to: `messages`, `messaging_postbacks`
3. For group thread events, ensure your app has the correct permissions

### 5. Make the Bot an Admin

- In the Instagram group chat, add the bot's Instagram account as an **admin**
- The bot MUST be admin to send messages to the thread

### 6. Test End-to-End

1. Add a new member to the Instagram group chat
2. Watch the terminal — you should see:
   ```
   member_added detected — thread=t_xxxx, members=['12345']
   ✅ Welcome message sent — thread=t_xxxx, message_id=m_xxxx
   ```
3. The welcome message appears in the group chat 🎉

---

## ⚠️ Known Gotchas

| Issue | Solution |
|-------|----------|
| **ngrok session expires** | Free tier expires after 2h. Restart ngrok and update the webhook URL in Meta Dashboard |
| **Bot is not admin** | You get a 403 permission error. Add the bot as admin in the group chat settings |
| **Duplicate events** | Meta sends webhooks at-least-once. The bot may send duplicate welcomes — acceptable for this use case |
| **Rate limiting** | Meta allows ~200 API calls/hour per Page. One welcome per member_added is well within limits |
| **Token expired** | APScheduler auto-refreshes every 50 days. If you see 401 errors, manually refresh via `token_refresh.py` |

---

## 🛡️ Security

- **HMAC-SHA256** signature verification on every webhook POST
- **Environment variables** for all secrets (never hardcoded)
- **XSS eliminated** from frontend (no `dangerouslySetInnerHTML`)
- **ErrorBoundary** prevents full app crashes from render errors

---

## 📊 Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React | 19.x |
| Bundler | Vite | 8.x |
| Backend | FastAPI | 0.111.0 |
| Server | Uvicorn | 0.29.0 |
| HTTP | httpx | 0.27.0 |
| Scheduler | APScheduler | 3.10.4 |
| API | Meta Graph API | v19.0 |

---

*Built with the Shadow System protocol. Arise, Hunter.* ⚔️
