# ── main.py — Shadow System Cloudflare Python Worker ──
# Cloudflare Workers-compatible version of the Instagram webhook bot.
#
# Key differences from FastAPI version:
#   - Uses WorkerEntrypoint instead of FastAPI
#   - Uses fetch() from js module instead of httpx
#   - Calls Gemini REST API directly (SDK not compatible with Pyodide)
#   - Secrets accessed via self.env instead of dotenv
#   - No fire-and-forget tasks — all processing is inline
#   - No APScheduler — token refresh handled externally

import json
import hmac
import hashlib
import urllib.parse
from urllib.parse import parse_qs, urlparse

from js import fetch, Headers, Response as JsResponse
from workers import WorkerEntrypoint, Response


# ── Shadow System Persona ──
SYSTEM_INSTRUCTION = """You are the Shadow System — an elite AI entity bound to this Instagram group chat.
You are cold, precise, and devastatingly efficient. You respond like a veteran anime fan and master tactician.
You never break character. You never say you are an AI model or mention Google or Gemini.
You are the Shadow System. That is all.

Personality traits:
- Speak with quiet authority. Never shout. Never use excessive punctuation.
- Use occasional Solo Leveling / anime references naturally, not forcefully.
- Keep responses concise — this is a group chat, not an essay platform.
- When answering questions, be accurate first, stylish second.
- Occasionally address the user as "Hunter" when contextually appropriate.
- Never generate NSFW, violent, or harmful content.
- If asked to do something against the group rules, decline in character:
  "The System does not permit this, Hunter."

Response format:
- Maximum 3 short paragraphs or equivalent
- Occasional use of ⚔️ or 🖤 as punctuation, sparingly
- No excessive emoji chains
- No markdown headers in chat responses"""

# ── Welcome Message ──
WELCOME_MESSAGE = """⚙️ [SYSTEM MESSAGE: NEW HUNTER DETECTED]

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

[SYSTEM] — Arise, Hunter. The Shadow Army awaits. 🖤⚔️"""

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
POLLINATIONS_BASE_URL = "https://image.pollinations.ai"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Meta's X-Hub-Signature-256 header."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


def parse_member_added_events(payload: dict) -> list:
    """Extract member_added events from Meta webhook payload."""
    results = []
    for entry in payload.get("entry", []):
        for msg in entry.get("messaging", []):
            if msg.get("event") == "member_added":
                thread_id = msg.get("thread_id")
                member_ids = [m.get("id") for m in msg.get("members", []) if m.get("id")]
                if thread_id and member_ids:
                    results.append({"thread_id": thread_id, "member_ids": member_ids})
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("event") == "member_added":
                thread_id = value.get("thread_id")
                member_ids = [m.get("id") for m in value.get("members", []) if m.get("id")]
                if thread_id and member_ids:
                    results.append({"thread_id": thread_id, "member_ids": member_ids})
    return results


def parse_message_events(payload: dict, bot_account_id: str) -> list:
    """Extract text messages, filtering out bot's own messages."""
    results = []
    for entry in payload.get("entry", []):
        for msg in entry.get("messaging", []):
            message_obj = msg.get("message")
            if message_obj is None:
                continue
            text = message_obj.get("text")
            if not text or not text.strip():
                continue
            sender_id = msg.get("sender", {}).get("id", "")
            thread_id = msg.get("thread_id", "") or msg.get("recipient", {}).get("id", "")
            if not sender_id or not thread_id:
                continue
            if sender_id == bot_account_id:
                continue
            results.append({
                "sender_id": sender_id,
                "thread_id": thread_id,
                "text": text.strip(),
            })
    return results


def detect_command(message: dict, bot_username: str) -> dict:
    """Classify a message as mention/ask/imagine/none."""
    text = message["text"]
    base = {
        "sender_id": message["sender_id"],
        "thread_id": message["thread_id"],
    }

    # @mention
    mention_prefix = f"@{bot_username}"
    if text.lower().startswith(mention_prefix.lower()):
        remaining = text[len(mention_prefix):].strip()
        if remaining:
            return {**base, "type": "mention", "text": remaining}
        return {**base, "type": "none", "text": ""}

    # /ask
    if text.lower().startswith("/ask "):
        remaining = text[5:].strip()
        if remaining:
            return {**base, "type": "ask", "text": remaining}
        return {**base, "type": "none", "text": ""}

    # /imagine
    if text.lower().startswith("/imagine "):
        remaining = text[9:].strip()
        if remaining:
            return {**base, "type": "imagine", "text": remaining}
        return {**base, "type": "none", "text": ""}

    return {**base, "type": "none", "text": ""}


def generate_image_url(prompt: str) -> str:
    """Build a Pollinations.ai image URL from a text prompt."""
    encoded = urllib.parse.quote(prompt, safe="")
    return (
        f"{POLLINATIONS_BASE_URL}/prompt/{encoded}"
        f"?width=1024&height=1024&model=flux&nologo=true&enhance=true"
    )


# ═══════════════════════════════════════════════════════════════
# API Callers (using JS fetch via FFI)
# ═══════════════════════════════════════════════════════════════

async def call_gemini(user_text: str, api_key: str) -> str:
    """Call Gemini REST API directly (SDK not compatible with Pyodide)."""
    url = f"{GEMINI_API_URL}?key={api_key}"
    body = json.dumps({
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": [
            {"parts": [{"text": user_text}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 500,
            "temperature": 0.8,
        }
    })

    headers = Headers.new({"Content-Type": "application/json"})
    response = await fetch(url, {
        "method": "POST",
        "headers": headers,
        "body": body,
    })

    if not response.ok:
        return "The System encountered interference. Try again, Hunter. ⚔️"

    data = (await response.json()).to_py()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return "The System encountered interference. Try again, Hunter. ⚔️"


async def send_meta_message(thread_id: str, message_payload: dict, access_token: str):
    """Send a message to Instagram via Meta Graph API."""
    url = f"{GRAPH_API_BASE}/me/messages"
    body = json.dumps({
        "recipient": {"thread_key": thread_id},
        "message": message_payload,
        "access_token": access_token,
    })
    headers = Headers.new({"Content-Type": "application/json"})
    await fetch(url, {
        "method": "POST",
        "headers": headers,
        "body": body,
    })


async def send_text_reply(thread_id: str, text: str, access_token: str):
    """Send a text message to a thread."""
    await send_meta_message(thread_id, {"text": text}, access_token)


async def send_image_message(thread_id: str, image_url: str, access_token: str):
    """Send an image attachment to a thread."""
    await send_meta_message(
        thread_id,
        {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True},
            }
        },
        access_token,
    )


async def send_welcome(thread_id: str, access_token: str):
    """Send the Shadow System welcome message."""
    await send_text_reply(thread_id, WELCOME_MESSAGE, access_token)


# ═══════════════════════════════════════════════════════════════
# Cloudflare Worker Entrypoint
# ═══════════════════════════════════════════════════════════════

class Default(WorkerEntrypoint):
    """
    Shadow System — Cloudflare Python Worker.

    Handles Instagram webhook verification (GET) and event processing (POST).
    Secrets are accessed via self.env (set via `wrangler secret put`).
    """

    async def fetch(self, request):
        url = urlparse(str(request.url))
        path = url.path
        method = str(request.method).upper()

        # ── Health Check ──
        if path == "/health":
            return Response.json({"status": "alive", "service": "shadow-system-bot", "version": "3.0.0-cf"})

        # ── Webhook Verification (GET) ──
        if path == "/webhook" and method == "GET":
            return await self._handle_verification(url.query)

        # ── Webhook Events (POST) ──
        if path == "/webhook" and method == "POST":
            return await self._handle_webhook(request)

        # ── 404 ──
        return Response("Not Found", status=404)

    async def _handle_verification(self, query_string: str):
        """Handle Meta's GET webhook verification challenge."""
        params = parse_qs(query_string or "")
        hub_mode = params.get("hub.mode", [None])[0]
        hub_token = params.get("hub.verify_token", [None])[0]
        hub_challenge = params.get("hub.challenge", [None])[0]

        if hub_mode == "subscribe" and hub_token == str(self.env.VERIFY_TOKEN):
            return Response(hub_challenge or "", headers={"Content-Type": "text/plain"})

        return Response("Verification failed", status=403)

    async def _handle_webhook(self, request):
        """Handle Meta's POST webhook events."""
        # Read raw body for signature verification
        body_text = await request.text()
        body_bytes = body_text.encode("utf-8")

        # Verify HMAC signature
        signature = request.headers.get("X-Hub-Signature-256") or ""
        if not verify_signature(body_bytes, signature, str(self.env.APP_SECRET)):
            return Response("Invalid signature", status=403)

        # Parse JSON payload
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            return Response("Invalid JSON", status=400)

        access_token = str(self.env.INSTA_TOKEN)
        bot_username = str(self.env.BOT_USERNAME)
        bot_account_id = str(self.env.INSTAGRAM_ACCOUNT_ID)
        gemini_key = str(self.env.GEMINI_KEY)

        # ── Process member_added events ──
        for event in parse_member_added_events(payload):
            try:
                await send_welcome(event["thread_id"], access_token)
            except Exception:
                pass  # Log in production — Workers have console.log via js module

        # ── Process AI commands ──
        messages = parse_message_events(payload, bot_account_id)
        for msg in messages:
            cmd = detect_command(msg, bot_username)
            if cmd["type"] == "none":
                continue

            try:
                if cmd["type"] in ("mention", "ask"):
                    result = await call_gemini(cmd["text"], gemini_key)
                    await send_text_reply(cmd["thread_id"], result, access_token)
                elif cmd["type"] == "imagine":
                    img_url = generate_image_url(cmd["text"])
                    await send_image_message(cmd["thread_id"], img_url, access_token)
            except Exception:
                pass  # Silently continue — don't crash the webhook response

        return Response.json({"status": "ok"})
