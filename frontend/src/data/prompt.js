// ── Shadow System Prompt Data ──
// All content, sections, stats, and usage steps

export const PROMPT = `<role>
You are an Elite Senior Backend Engineer — a Monarch-level architect specializing in the Meta Graph API, Python async systems, and production-grade webhook infrastructure. You operate with the precision of a Shadow Extraction system: no wasted code, no ambiguity, no half-measures.
</role>

<thinking_directive>
Before writing a single line of code, engage your full reasoning depth:

1. MAP THE ARCHITECTURE — Trace the complete data flow: Instagram event → Meta Webhook POST → Signature Verification → Payload Parsing → Graph API reply. Identify every failure point.

2. INTERROGATE THE META API — Reason through the exact webhook payload shape for Instagram group thread activity. What does the \`entry[].messaging[]\` or \`entry[].changes[]\` tree actually look like for a \`member_added\` event? Where does \`thread_id\` live? Where do \`member_ids\` live? Are there edge cases where the payload shape differs?

3. AUDIT THE TOKEN LIFECYCLE — A short-lived token dies in 1 hour. A long-lived token dies in 60 days. A never-expiring Page Token exists for certain configurations. Reason through which token type is correct here, how to obtain it, and how to programmatically refresh it without human intervention.

4. SECURITY THREAT MODEL — What happens if a malicious actor discovers the webhook URL? Reason through the HMAC-SHA256 signature verification flow using \`X-Hub-Signature-256\`. What are the failure modes if this is skipped?

5. PRODUCTION READINESS CHECKLIST — Before finalizing output, mentally run through: error handling, API rate limits, async vs sync, logging, environment variable management, local dev tooling (ngrok), and deployment path.
</thinking_directive>

<objective>
Build a complete, production-ready Python automation bot for an Instagram Group Chat. The bot must:

- Listen for webhook events from the Meta Graph API using FastAPI
- Detect the exact moment a new member joins the group thread (\`member_added\` activity type)
- Instantly POST a formatted welcome message to that thread via the Graph API
- Run indefinitely with zero token expiry downtime
- Be launchable from VS Code with a single terminal command
</objective>

<technical_requirements>
Language:         Python 3.11+
Framework:        FastAPI + Uvicorn
HTTP Client:      requests or httpx (async preferred)
Env Management:   python-dotenv
Token Scheduler:  APScheduler (background job, every 50 days)
Security:         HMAC-SHA256 signature validation on every POST
Local Tunneling:  ngrok (document the exact commands)
API Version:      Meta Graph API v19.0
</technical_requirements>

<welcome_message_payload>
The bot must send EXACTLY the following text when a member_added event fires:

⚙️ [SYSTEM MESSAGE: NEW HUNTER DETECTED]

"A new presence has entered the instance. Welcome to the Raid Party. Before you Arise, you must acknowledge the Laws of the Monarch."

⚔️ HUNTER QUALIFICATIONS
• The Awakening:      Must be an anime lover. 💖
• Dungeon Experience: Cleared at least 5 Anime Gates. 📺
• The Summoning:      Reveal your primary Waifu/Husbando. 💫

📜 COMMANDMENTS OF THE SYSTEM

1️⃣  Respect all anime & opinions. No toxicity. 🤝
2️⃣  No fights. Violators will be purged. 🚫🔥
3️⃣  No spoilers without ⚠️ tags.
4️⃣  Stay active or be removed from the party. 💬
5️⃣  Anime content ONLY. 🎌
6️⃣  No NSFW or adult content. This dungeon is sacred ground. 🔞🚫
7️⃣  No profanity or foul language. Keep comms clean, Hunter. 🧼✨

📊 INTRO FORMAT (PLAYER PROFILE)
┌─────────────────────────┐
│  Name:                  │
│  Age:                   │
│  From:                  │
│  Fav Anime:             │
│  Fav Character:         │
│  Anime Count:           │
└─────────────────────────┘

[SYSTEM] — Arise, Hunter. The Shadow Army awaits. 🖤⚔️
</welcome_message_payload>

<deliverables>
Produce ALL of the following, in order:

1. PROJECT STRUCTURE
   Show the full file tree with one-line descriptions per file.

2. requirements.txt
   Every dependency pinned to a stable version.

3. .env.example
   All required environment variables with inline comments explaining how to obtain each one.

4. config.py
   Centralized env loading. Fail loudly on startup if any required var is missing.

5. bot.py
   - \`parse_member_added_event(payload: dict) -> list[dict]\`
     Handle BOTH the \`messaging\` and \`changes\` payload formats Meta may send.
     Extract \`thread_id\` and \`member_ids\` from the correct nesting level.
     Add inline comments explaining WHY each key is accessed.
   - \`send_welcome_message(thread_id: str) -> dict\`
     POST to /me/messages with the exact welcome payload above.
     Log success and surface API errors clearly.

6. token_refresh.py
   - \`exchange_for_long_lived_token(short_lived_token: str) -> str\`
     One-time CLI-runnable function. Add a usage docstring with the exact python -c command.
   - \`refresh_long_lived_token() -> None\`
     Callable by the scheduler. Must persist the new token back to .env AND hot-reload config.PAGE_ACCESS_TOKEN in memory.
   - \`_update_env_token(new_token: str) -> None\`
     Atomic .env rewrite. Handle file I/O errors gracefully.

7. main.py
   - FastAPI app with APScheduler lifespan context manager
   - GET /webhook — Meta verification handshake (hub.mode, hub.verify_token, hub.challenge)
   - POST /webhook — Full pipeline: signature check → JSON parse → event dispatch → 200 OK
   - Detailed inline comments on the Meta webhook contract (why 200 must be instant, etc.)

8. STEP-BY-STEP SETUP GUIDE
   Numbered instructions covering:
   a. pip install
   b. Generating the initial Long-Lived Page Token (exact Graph API Explorer steps)
   c. Starting uvicorn
   d. ngrok tunnel command + what the output looks like
   e. Registering the Callback URL in the Meta App Dashboard (exact UI path)
   f. Subscribing to the correct webhook fields for Instagram group thread events
   g. Making the bot an Admin of the group chat
   h. Testing the full flow end-to-end

9. PAYLOAD ANATOMY (diagram)
   Show a realistic example of the raw JSON Meta sends for a member_added event.
   Annotate each field with what it means and whether it's required or optional.

10. KNOWN GOTCHAS & SOLUTIONS
    Address at minimum:
    - Instagram vs Facebook object type differences in the webhook
    - Rate limiting on /me/messages
    - ngrok session expiry during development
    - What happens when the bot is NOT an admin (permission errors)
    - Duplicate event delivery (Meta sends webhooks at-least-once)
</deliverables>

<output_format>
- Use clear file headers (# ── filename.py ──) before each code block
- All code blocks must be syntax-highlighted Python or JSON
- Inline comments are MANDATORY on any non-obvious line
- Production quality: no TODOs, no placeholder logic, no "add your logic here"
- If any Meta API behavior is undocumented or ambiguous, state your assumption explicitly and reason through the most likely correct behavior
</output_format>`;

export const SECTIONS = [
  {
    id: "role",
    label: "ROLE",
    icon: "👤",
    color: "#7c3aed",
    tag: "<role>",
    description: "Elite Senior Backend Engineer persona with Monarch-level specialization",
  },
  {
    id: "thinking",
    label: "THINKING DIRECTIVE",
    icon: "🧠",
    color: "#0891b2",
    tag: "<thinking_directive>",
    description: "5-step deep reasoning framework before code generation",
  },
  {
    id: "objective",
    label: "OBJECTIVE",
    icon: "🎯",
    color: "#059669",
    tag: "<objective>",
    description: "Production-ready Instagram Group Chat bot requirements",
  },
  {
    id: "technical",
    label: "TECH REQUIREMENTS",
    icon: "⚙️",
    color: "#d97706",
    tag: "<technical_requirements>",
    description: "Python 3.11+, FastAPI, httpx, APScheduler, HMAC-SHA256",
  },
  {
    id: "welcome",
    label: "WELCOME PAYLOAD",
    icon: "💬",
    color: "#dc2626",
    tag: "<welcome_message_payload>",
    description: "Solo Leveling-themed welcome message for new hunters",
  },
  {
    id: "deliverables",
    label: "DELIVERABLES",
    icon: "📦",
    color: "#7c3aed",
    tag: "<deliverables>",
    description: "10 complete outputs: code, guides, diagrams, and gotchas",
  },
  {
    id: "format",
    label: "OUTPUT FORMAT",
    icon: "📄",
    color: "#0891b2",
    tag: "<output_format>",
    description: "Strict production quality standards and formatting rules",
  },
];

export const STATS = [
  { label: "TOKENS EST.", value: "~2,400", icon: "🔢", detail: "Prompt size" },
  { label: "THINKING DEPTH", value: "MAX", icon: "🧠", detail: "Extended" },
  { label: "DELIVERABLES", value: "10", icon: "📦", detail: "Complete" },
  { label: "GOTCHAS COVERED", value: "5+", icon: "⚠️", detail: "Known issues" },
  { label: "API VERSION", value: "v19.0", icon: "🔗", detail: "Meta Graph" },
  { label: "SECURITY", value: "HMAC", icon: "🔒", detail: "SHA-256" },
];

export const USAGE_STEPS = [
  {
    step: "01",
    title: "Open claude.ai",
    desc: "Navigate to claude.ai and start a fresh conversation. Select Claude Opus 4.6 from the model dropdown.",
    accent: "claude.ai/new",
    icon: "🌐",
  },
  {
    step: "02",
    title: "Enable Extended Thinking",
    desc: "Click the brain icon before sending. Set the thinking budget to Extended or Max for optimal reasoning depth.",
    accent: "Extended Thinking → ON",
    icon: "🧠",
  },
  {
    step: "03",
    title: "Copy & Paste Prompt",
    desc: "Use the copy button above to grab the full prompt. Paste it as your first and only message — no extra text.",
    accent: "⌘V → Enter",
    icon: "📋",
  },
  {
    step: "04",
    title: "Watch It Think",
    desc: "Opus will reason through the full architecture before writing a single line. The thinking stream reveals deep analysis.",
    accent: "~60–120s reasoning",
    icon: "⏳",
  },
  {
    step: "05",
    title: "Receive All 10 Deliverables",
    desc: "Complete Python project files, setup guide, payload anatomy diagram, and comprehensive gotcha documentation.",
    accent: "10 complete deliverables",
    icon: "📦",
  },
  {
    step: "06",
    title: "Deploy & Launch",
    desc: "Drop files into a folder, pip install, configure .env, start uvicorn, tunnel with ngrok. The bot goes live.",
    accent: "uvicorn main:app --reload",
    icon: "🚀",
  },
];
