# ── main.py — Shadow System Cloudflare Python Worker ──
# REWRITE: 2026-04-28 — Eliminated Error 1101 via defensive architecture.
#
# Architecture notes:
#   - Uses `from js import Response` for ALL outgoing responses (most reliable
#     path in Pyodide — bypasses any workers-sdk abstraction issues).
#   - Global try/except in fetch() guarantees NO unhandled exception ever.
#   - Every env binding checked with getattr() before use.
#   - Webhook handshake returns ONLY hub.challenge as plain text.
#   - Non-API routes fall through to env.ASSETS.fetch() for the React frontend.

import json
import hmac
import hashlib
import urllib.parse
from urllib.parse import parse_qs, urlparse

from js import Response
from workers import WorkerEntrypoint

# NOTE: `from js import fetch, Headers` is intentionally NOT at module level.
# The 2026 Pyodide/3.13 runtime creates a memory snapshot at deploy time.
# JS proxy objects (JsProxy) cannot be serialized into this snapshot.
# `Response` is safe at module level because it is a constructor, not an instance.
# `fetch` and `Headers` are lazily imported inside async functions that need them.


# ═══════════════════════════════════════════════════════════════
# Response Helpers — always return a valid JS Response, never crash
#
# CRITICAL: JS Response() constructor signature is:
#   new Response(body, init)
# where `init` is a plain object {status, headers, ...}.
# Pyodide does NOT translate Python **kwargs into a JS object.
# We MUST pass the init dict as a POSITIONAL argument.
# ═══════════════════════════════════════════════════════════════

def _text_response(body="", status=200, content_type="text/plain"):
    """Return a plain-text JS Response. Safe to call anywhere."""
    # Force body to string AND use list-of-lists for headers.
    # This is the most "Sequence-friendly" format for Pyodide —
    # avoids the TypeError that causes Error 1101.
    try:
        safe_body = str(body) if body is not None else ""
        headers = [["Content-Type", str(content_type)]]
        return Response.new(safe_body, {"status": int(status), "headers": headers})
    except Exception:
        # Absolute last resort — bare Response with no options
        return Response.new(str(body) if body is not None else "")


def _json_response(data=None, status=200):
    """Return a JSON JS Response. Safe to call anywhere."""
    try:
        json_str = json.dumps(data if data is not None else {})
        headers = [["Content-Type", "application/json"]]
        return Response.new(json_str, {"status": int(status), "headers": headers})
    except Exception:
        return Response.new(str(data) if data is not None else "{}")


def _error_response(message="Unknown error", status=500):
    """Return a Shadow System debug error response. Never crashes."""
    # Ensure we aren't passing a None object to the text helper
    return _text_response(f"Shadow System Debug: {str(message)}", status=int(status))


# ═══════════════════════════════════════════════════════════════
# Shadow System Persona
# ═══════════════════════════════════════════════════════════════

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
# API Callers (using JS fetch via FFI — LAZY IMPORTS)
# ═══════════════════════════════════════════════════════════════

async def call_gemini(user_text: str, api_key: str) -> str:
    """Call Gemini REST API directly (SDK not compatible with Pyodide)."""
    from js import fetch, Headers  # Lazy import — avoids snapshot serialization

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
    from js import fetch, Headers  # Lazy import — avoids snapshot serialization

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

    DEFENSIVE DESIGN:
    - Every code path is wrapped in try/except.
    - Missing env bindings return human-readable errors (not Error 1101).
    - The fetch() method can NEVER throw an unhandled exception.
    """

    async def fetch(self, request):
        # ── GLOBAL TRY/EXCEPT — the 1101 kill-switch ──
        try:
            url = urlparse(str(request.url))
            path = url.path
            method = str(request.method).upper()

            # ── Health Check ──
            if path == "/health":
                return _json_response({
                    "status": "alive",
                    "service": "shadow-system-bot",
                    "version": "3.1.0-cf",
                })

            # ── Webhook Verification (GET) ──
            if path == "/webhook" and method == "GET":
                return self._handle_verification(url.query)

            # ── Webhook Events (POST) ──
            if path == "/webhook" and method == "POST":
                return await self._handle_webhook(request)

            # ── Serve React Frontend (Static Assets) ──
            # Forward all non-API requests to Cloudflare's asset server.
            assets = getattr(self.env, "ASSETS", None)
            if assets is None:
                return _error_response(
                    "Missing ASSETS binding in Dashboard. "
                    "Add [assets] directory in wrangler.toml and redeploy.",
                    status=503,
                )
            return await assets.fetch(request)

        except Exception as exc:
            # ── LAST RESORT — guarantee a valid Response ──
            try:
                return _error_response(str(type(exc).__name__) + ": " + str(exc))
            except Exception:
                # If even _error_response fails, return the most basic Response possible
                return Response.new("Shadow System Debug: internal error")

    def _handle_verification(self, query_string: str):
        """
        Handle Meta's GET webhook verification challenge.

        Returns ONLY the hub.challenge value as plain text on success.
        """
        # ── Check env.VERIFY_TOKEN exists ──
        verify_token = getattr(self.env, "VERIFY_TOKEN", None)
        if verify_token is None:
            return _error_response(
                "Missing VERIFY_TOKEN in Dashboard. "
                "Run: npx wrangler secret put VERIFY_TOKEN",
                status=503,
            )

        # ── Parse query parameters ──
        params = parse_qs(query_string or "")
        hub_mode = params.get("hub.mode", [None])[0]
        hub_token = params.get("hub.verify_token", [None])[0]
        hub_challenge = params.get("hub.challenge", [None])[0]

        # ── Validate handshake ──
        if hub_mode != "subscribe":
            return _error_response(
                f"Invalid hub.mode: expected 'subscribe', got '{hub_mode}'",
                status=403,
            )

        if hub_token != str(verify_token):
            return _error_response(
                "hub.verify_token does not match VERIFY_TOKEN secret",
                status=403,
            )

        if not hub_challenge:
            return _error_response("Missing hub.challenge parameter", status=400)

        # ── SUCCESS: Return ONLY the challenge as plain text ──
        return _text_response(str(hub_challenge))

    async def _handle_webhook(self, request):
        """Handle Meta's POST webhook events."""
        from js import console  # Lazy import — Workers logging via JS console

        # ── Validate required env bindings ──
        app_secret = getattr(self.env, "APP_SECRET", None)
        if app_secret is None:
            return _error_response("Missing APP_SECRET in Dashboard", status=503)

        insta_token = getattr(self.env, "INSTA_TOKEN", None)
        if insta_token is None:
            return _error_response("Missing INSTA_TOKEN in Dashboard", status=503)

        bot_username = getattr(self.env, "BOT_USERNAME", None)
        if bot_username is None:
            return _error_response("Missing BOT_USERNAME in Dashboard", status=503)

        bot_account_id = getattr(self.env, "INSTAGRAM_ACCOUNT_ID", None)
        if bot_account_id is None:
            return _error_response("Missing INSTAGRAM_ACCOUNT_ID in Dashboard", status=503)

        gemini_key = getattr(self.env, "GEMINI_KEY", None)
        if gemini_key is None:
            return _error_response("Missing GEMINI_KEY in Dashboard", status=503)

        # ── Read raw body for signature verification ──
        body_text = await request.text()
        body_bytes = body_text.encode("utf-8")

        # ── Verify HMAC signature ──
        signature = request.headers.get("X-Hub-Signature-256") or ""
        if not verify_signature(body_bytes, signature, str(app_secret)):
            return _text_response("Invalid signature", status=403)

        # ── Parse JSON payload ──
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            return _text_response("Invalid JSON", status=400)

        access_token = str(insta_token)
        username = str(bot_username)
        account_id = str(bot_account_id)
        g_key = str(gemini_key)

        # ── Process member_added events ──
        for event in parse_member_added_events(payload):
            try:
                await send_welcome(event["thread_id"], access_token)
            except Exception as e:
                console.error(f"[Shadow System] Welcome failed: {e}")

        # ── Process AI commands ──
        messages = parse_message_events(payload, account_id)
        for msg in messages:
            cmd = detect_command(msg, username)
            if cmd["type"] == "none":
                continue

            try:
                if cmd["type"] in ("mention", "ask"):
                    result = await call_gemini(cmd["text"], g_key)
                    await send_text_reply(cmd["thread_id"], result, access_token)
                elif cmd["type"] == "imagine":
                    img_url = generate_image_url(cmd["text"])
                    await send_image_message(cmd["thread_id"], img_url, access_token)
            except Exception as e:
                console.error(f"[Shadow System] Command '{cmd['type']}' failed: {e}")

        return _json_response({"status": "ok"})
