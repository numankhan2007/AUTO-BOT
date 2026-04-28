# ── main.py — Shadow System Cloudflare Python Worker ──
# REWRITE: 2026-04-28 — Fixed 500 crash + corrected Meta Send Message API format.
#
# Architecture notes:
#   - Uses `from js import Response` for ALL outgoing responses (most reliable
#     path in Pyodide — bypasses any workers-sdk abstraction issues).
#   - Global try/except in fetch() guarantees NO unhandled exception ever.
#   - Every env binding checked with getattr() before use.
#   - Webhook handshake returns ONLY hub.challenge as plain text.
#   - Non-API routes fall through to env.ASSETS.fetch() for the React frontend.
#
# Instagram API Limitation:
#   The Instagram Messaging API ONLY supports 1:1 (DM) conversations.
#   Group chat messaging is NOT supported by Meta for third-party apps.
#   This bot operates exclusively in Direct Messages.

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

SYSTEM_INSTRUCTION = """You are the Shadow System — an elite AI entity bound to Instagram DMs.
You are cold, precise, and devastatingly efficient. You respond like a veteran anime fan and master tactician.
You never break character. You never say you are an AI model or mention Google or Gemini.
You are the Shadow System. That is all.

Personality traits:
- Speak with quiet authority. Never shout. Never use excessive punctuation.
- Use occasional Solo Leveling / anime references naturally, not forcefully.
- Keep responses concise — this is a DM chat, not an essay platform.
- When answering questions, be accurate first, stylish second.
- Occasionally address the user as "Hunter" when contextually appropriate.
- Never generate NSFW, violent, or harmful content.
- If asked to do something against the rules, decline in character:
  "The System does not permit this, Hunter."

Response format:
- Maximum 3 short paragraphs or equivalent
- Occasional use of ⚔️ or 🖤 as punctuation, sparingly
- No excessive emoji chains
- No markdown headers in chat responses"""

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
POLLINATIONS_BASE_URL = "https://image.pollinations.ai"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def _safe_str(value, default=""):
    """Safely convert a JsProxy or any value to a Python string.

    Pyodide's request.headers.get() returns JsProxy objects, not Python strings.
    Calling Python string methods on them (like .startswith()) can crash.
    This function ensures we always have a real Python str.
    """
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Meta's X-Hub-Signature-256 header."""
    sig = _safe_str(signature)
    if not sig or not sig.startswith("sha256="):
        return False
    expected = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig[7:])


def parse_message_events(payload: dict, bot_account_id: str) -> list:
    """Extract text messages from webhook payload, filtering out bot's own messages.

    Handles the standard Instagram webhook format:
    {
        "object": "instagram",
        "entry": [{
            "id": "IGID",
            "messaging": [{
                "sender": {"id": "IGSID"},
                "recipient": {"id": "IGID"},
                "message": {"mid": "...", "text": "..."}
            }]
        }]
    }
    """
    results = []
    for entry in payload.get("entry", []):
        for msg in entry.get("messaging", []):
            message_obj = msg.get("message")
            if message_obj is None:
                continue

            # Skip echo messages (messages sent BY the bot itself)
            if message_obj.get("is_echo"):
                continue

            text = message_obj.get("text")
            if not text or not str(text).strip():
                continue

            sender_id = _safe_str(msg.get("sender", {}).get("id", ""))
            recipient_id = _safe_str(msg.get("recipient", {}).get("id", ""))

            if not sender_id:
                continue

            # Skip if the sender IS the bot (double-check)
            if sender_id == str(bot_account_id):
                continue

            results.append({
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "text": str(text).strip(),
                "mid": _safe_str(message_obj.get("mid", "")),
            })
    return results


def detect_command(message: dict) -> dict:
    """Classify a DM message as imagine/ask/chat.

    In DMs (1:1), every message triggers a response.
    - /imagine <prompt> → generate image
    - /ask <question> → explicit Gemini query (same as chat, but explicit)
    - anything else → chat with Gemini AI

    No @mention detection needed in DMs since it's always 1:1.
    """
    text = message["text"]
    base = {
        "sender_id": message["sender_id"],
        "mid": message.get("mid", ""),
    }

    # /imagine — generate an image
    if text.lower().startswith("/imagine "):
        remaining = text[9:].strip()
        if remaining:
            return {**base, "type": "imagine", "text": remaining}
        return {**base, "type": "chat", "text": "What image would you like me to create, Hunter?"}

    # /ask — explicit question (functionally same as chat)
    if text.lower().startswith("/ask "):
        remaining = text[5:].strip()
        if remaining:
            return {**base, "type": "chat", "text": remaining}
        return {**base, "type": "chat", "text": "Ask me anything, Hunter."}

    # /help — show available commands
    if text.lower().strip() in ("/help", "/commands", "/start"):
        return {**base, "type": "help", "text": ""}

    # Default: chat with Gemini AI — EVERY DM gets a response
    return {**base, "type": "chat", "text": text}


def generate_image_url(prompt: str) -> str:
    """Build a Pollinations.ai image URL from a text prompt."""
    encoded = urllib.parse.quote(prompt, safe="")
    return (
        f"{POLLINATIONS_BASE_URL}/prompt/{encoded}"
        f"?width=1024&height=1024&model=flux&nologo=true&enhance=true"
    )


HELP_MESSAGE = """⚔️ Shadow System — Command Protocol

Available commands:
• Just type anything → I'll respond (AI chat)
• /imagine <prompt> → Generate an image
• /ask <question> → Ask me anything
• /help → Show this message

The System awaits your command, Hunter. 🖤"""


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
        error_text = await response.text()
        return f"The System encountered interference. (HTTP {response.status}) ⚔️"

    data = (await response.json()).to_py()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return "The System encountered interference. Try again, Hunter. ⚔️"


async def send_text_reply(sender_id: str, text: str, access_token: str):
    """Send a text message to a user via Instagram DM.

    Uses the correct Meta Graph API format:
    - POST /me/messages?access_token=<TOKEN>
    - recipient: {"id": "<IGSID>"}  (Instagram-Scoped User ID)
    - message: {"text": "<TEXT>"}
    """
    from js import fetch, Headers  # Lazy import — avoids snapshot serialization

    url = f"{GRAPH_API_BASE}/me/messages?access_token={access_token}"
    body = json.dumps({
        "recipient": {"id": sender_id},
        "message": {"text": text},
    })
    headers = Headers.new({"Content-Type": "application/json"})
    resp = await fetch(url, {
        "method": "POST",
        "headers": headers,
        "body": body,
    })
    return resp


async def send_image_message(sender_id: str, image_url: str, access_token: str):
    """Send an image attachment to a user via Instagram DM.

    Uses the correct Meta Graph API format:
    - POST /me/messages?access_token=<TOKEN>
    - recipient: {"id": "<IGSID>"}
    - message: {"attachment": {"type": "image", "payload": {"url": "..."}}}
    """
    from js import fetch, Headers  # Lazy import — avoids snapshot serialization

    url = f"{GRAPH_API_BASE}/me/messages?access_token={access_token}"
    body = json.dumps({
        "recipient": {"id": sender_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True},
            }
        },
    })
    headers = Headers.new({"Content-Type": "application/json"})
    resp = await fetch(url, {
        "method": "POST",
        "headers": headers,
        "body": body,
    })
    return resp


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
                    "version": "4.0.0-dm",
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

        # Force both to stripped Python strings — Pyodide JsProxy can add junk
        expected = str(verify_token).strip()
        received = str(hub_token).strip() if hub_token else ""

        if received != expected:
            return _error_response(
                f"Token mismatch: got [{received}] (len={len(received)}) "
                f"vs expected [{expected}] (len={len(expected)})",
                status=403,
            )

        if not hub_challenge:
            return _error_response("Missing hub.challenge parameter", status=400)

        # ── SUCCESS: Return ONLY the challenge as plain text ──
        return _text_response(str(hub_challenge))

    async def _handle_webhook(self, request):
        """Handle Meta's POST webhook events (DMs only)."""
        from js import console  # Lazy import — Workers logging via JS console

        # ── Validate required env bindings ──
        required_secrets = [
            "APP_SECRET", "INSTA_TOKEN",
            "INSTAGRAM_ACCOUNT_ID", "GEMINI_KEY",
        ]
        missing = [s for s in required_secrets if getattr(self.env, s, None) is None]
        if missing:
            console.error(f"[Shadow System] FATAL: Missing secrets: {', '.join(missing)}")
            return _error_response(
                f"Missing secrets in Dashboard: {', '.join(missing)}",
                status=503,
            )

        app_secret = _safe_str(getattr(self.env, "APP_SECRET", None))
        insta_token = _safe_str(getattr(self.env, "INSTA_TOKEN", None))
        bot_account_id = _safe_str(getattr(self.env, "INSTAGRAM_ACCOUNT_ID", None))
        gemini_key = _safe_str(getattr(self.env, "GEMINI_KEY", None))

        console.log("[Shadow System] All secrets present. Processing webhook...")

        # ── Read raw body for signature verification ──
        try:
            body_text = _safe_str(await request.text())
        except Exception as e:
            console.error(f"[Shadow System] Failed to read request body: {e}")
            return _error_response("Failed to read request body", status=400)

        body_bytes = body_text.encode("utf-8")

        # ── Verify HMAC signature ──
        # Get header safely — JsProxy to Python str
        raw_sig = None
        try:
            raw_sig = request.headers.get("X-Hub-Signature-256")
        except Exception:
            pass
        signature = _safe_str(raw_sig)

        console.log(f"[Shadow System] Signature present: {bool(signature)}")

        if not verify_signature(body_bytes, signature, app_secret):
            console.error("[Shadow System] Signature verification FAILED")
            return _text_response("Invalid signature", status=403)

        console.log("[Shadow System] Signature verified OK")

        # ── Parse JSON payload ──
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError as e:
            console.error(f"[Shadow System] Invalid JSON: {e}")
            return _text_response("Invalid JSON", status=400)

        console.log(f"[Shadow System] Payload object type: {payload.get('object', 'unknown')}")

        # ── Only process Instagram webhook events ──
        if payload.get("object") != "instagram":
            console.log(f"[Shadow System] Ignoring non-instagram object: {payload.get('object')}")
            return _json_response({"status": "ignored"})

        # ── Process DM messages ──
        messages = parse_message_events(payload, bot_account_id)
        console.log(f"[Shadow System] Found {len(messages)} message(s) to process")

        for msg in messages:
            cmd = detect_command(msg)
            console.log(
                f"[Shadow System] Message from {msg['sender_id']}: "
                f"type={cmd['type']}, text={cmd['text'][:50]}..."
            )

            try:
                if cmd["type"] == "help":
                    resp = await send_text_reply(
                        cmd["sender_id"], HELP_MESSAGE, insta_token
                    )
                    resp_text = _safe_str(await resp.text())
                    console.log(f"[Shadow System] Help reply result: {resp.status} {resp_text[:200]}")

                elif cmd["type"] == "chat":
                    # Call Gemini AI
                    console.log("[Shadow System] Calling Gemini API...")
                    result = await call_gemini(cmd["text"], gemini_key)
                    console.log(f"[Shadow System] Gemini response length: {len(result)}")

                    # Send reply back to the sender
                    resp = await send_text_reply(
                        cmd["sender_id"], result, insta_token
                    )
                    resp_text = _safe_str(await resp.text())
                    console.log(f"[Shadow System] Send reply result: {resp.status} {resp_text[:200]}")

                elif cmd["type"] == "imagine":
                    # Generate image URL
                    img_url = generate_image_url(cmd["text"])
                    console.log(f"[Shadow System] Image URL: {img_url[:100]}")

                    # Send image
                    resp = await send_image_message(
                        cmd["sender_id"], img_url, insta_token
                    )
                    resp_text = _safe_str(await resp.text())
                    console.log(f"[Shadow System] Send image result: {resp.status} {resp_text[:200]}")

            except Exception as e:
                console.error(f"[Shadow System] Command '{cmd['type']}' failed: {type(e).__name__}: {e}")

        # ── MUST return 200 quickly — Meta expects it within 5 seconds ──
        return _json_response({"status": "ok"})
