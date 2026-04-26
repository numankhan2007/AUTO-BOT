# ── main.py — Shadow System Instagram Bot Server ──
# FastAPI application with Meta webhook integration.
#
# Endpoints:
#   GET  /webhook  — Meta verification handshake
#   POST /webhook  — Receive and process Instagram events
#   GET  /health   — Health check for monitoring
#
# Run with:
#   cd backend && uvicorn main:app --reload --port 8000

import hmac
import hashlib
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Query
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import bot
import token_refresh
import command_router
import ai_engine
import cooldown
from command_router import CommandType

# ── Logging Setup ──
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s │ %(name)-12s │ %(levelname)-8s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("shadow-bot")


# ── APScheduler Lifespan ──
# The scheduler runs token refresh as a background job.
# Using FastAPI's lifespan context manager ensures clean startup/shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Start APScheduler on app startup, shut it down on app shutdown.
    The token refresh job runs every TOKEN_REFRESH_DAYS (default: 50 days)
    to keep the long-lived token alive before its 60-day expiry.
    """
    scheduler = AsyncIOScheduler()

    # Schedule token refresh — asyncio-compatible wrapper
    def refresh_job():
        asyncio.get_event_loop().create_task(token_refresh.refresh_long_lived_token())

    scheduler.add_job(
        refresh_job,
        "interval",
        days=config.TOKEN_REFRESH_DAYS,
        id="token_refresh",
        name="Meta Token Refresh",
        replace_existing=True,
    )
    # Schedule cooldown cleanup — runs every hour to remove stale entries
    # and prevent unbounded memory growth in long-running processes
    scheduler.add_job(
        cooldown.cleanup_expired,
        "interval",
        hours=1,
        id="cooldown_cleanup",
        name="AI Cooldown Cleanup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "🗡️  Shadow System Bot online — token refresh every %d days, cooldown=%ds",
        config.TOKEN_REFRESH_DAYS,
        config.AI_COOLDOWN_SECONDS,
    )

    yield  # App is running

    scheduler.shutdown(wait=False)
    logger.info("🗡️  Shadow System Bot shutting down")


# ── FastAPI App ──
app = FastAPI(
    title="Shadow System Instagram Bot",
    description="Webhook server for Instagram group chat automation",
    version="1.0.0",
    lifespan=lifespan,
)


def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the HMAC-SHA256 signature from Meta's X-Hub-Signature-256 header.

    Meta signs every webhook POST with your App Secret. If we skip this check,
    any attacker who discovers the webhook URL can send forged events.

    The header format is: "sha256=<hex_digest>"
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        key=config.APP_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(expected, signature[7:])  # Strip "sha256=" prefix


@app.get("/webhook")
async def webhook_verify(
    # Meta sends these query params during webhook registration:
    # hub.mode=subscribe, hub.verify_token=<your_token>, hub.challenge=<random_string>
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta Webhook Verification Handshake.

    When you register a webhook URL in the Meta App Dashboard, Meta sends a GET
    request with a challenge string. You must:
    1. Verify hub.mode is "subscribe"
    2. Verify hub.verify_token matches your configured VERIFY_TOKEN
    3. Respond with the hub.challenge value as plain text

    If any check fails, return 403 to reject the registration.
    """
    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        logger.info("✅ Webhook verification successful")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning(
        "❌ Webhook verification failed — mode=%s, token_match=%s",
        hub_mode,
        hub_verify_token == config.VERIFY_TOKEN,
    )
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def webhook_receive(request: Request):
    """
    Receive and process Instagram webhook events.

    CRITICAL: Meta requires a 200 response within 20 seconds.
    If we don't respond in time, Meta marks the webhook as unhealthy
    and stops sending events after repeated failures.

    Strategy:
    1. Read raw body + verify HMAC signature (security)
    2. Parse JSON payload
    3. Extract member_added events
    4. Fire-and-forget the welcome message (don't block the 200 response)
    5. Return 200 OK immediately

    Meta sends webhooks at-least-once, meaning duplicate events are possible.
    For a welcome message bot, idempotency is acceptable (sending the message
    twice is better than missing it).
    """
    # Step 1: Read raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature):
        logger.warning("❌ Invalid webhook signature — possible forged request")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Step 2: Parse JSON
    try:
        payload = await request.json()
    except Exception:
        logger.error("❌ Failed to parse webhook JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.debug("Webhook payload received: %s", payload)

    # Step 3: Extract member_added events
    events = bot.parse_member_added_event(payload)

    # Step 4: Fire-and-forget — send welcome messages without blocking the response
    # This ensures we return 200 to Meta within the 20-second window
    for event in events:
        asyncio.create_task(
            _safe_send_welcome(event["thread_id"], event["member_ids"])
        )

    # ── Step 5: AI Message Event Routing ──
    # Parse text messages from the payload (self-reply prevention is built into
    # parse_message_event — bot's own messages are dropped before reaching here)
    messages = command_router.parse_message_event(payload)
    for msg in messages:
        cmd = command_router.detect_command(msg)

        if cmd.type == CommandType.NONE:
            # Not a bot command — silently discard. No API call, no reply, no log spam.
            continue

        if cooldown.is_on_cooldown(cmd.sender_id):
            # User is rate-limited — silently ignore to avoid wasting Meta API calls.
            # Debug log is emitted inside cooldown.is_on_cooldown() for monitoring.
            logger.debug("Cooldown active for sender %s — skipping", cmd.sender_id)
            continue

        # Record the request BEFORE dispatching — catches rapid duplicate clicks
        # even if the first AI request is still processing
        cooldown.record_request(cmd.sender_id)

        # Fire-and-forget the AI processing — returns 200 before AI responds
        asyncio.create_task(
            _safe_process_ai_request(cmd)
        )

    # Step 6: Return 200 immediately (Meta requires this)
    return {"status": "ok"}


async def _safe_send_welcome(thread_id: str, member_ids: list[str]):
    """
    Wrapper that catches exceptions from send_welcome_message.
    Prevents unhandled errors in fire-and-forget tasks from crashing the event loop.
    """
    try:
        await bot.send_welcome_message(thread_id)
        logger.info(
            "Welcome message dispatched for %d new member(s) in thread %s",
            len(member_ids),
            thread_id,
        )
    except Exception as e:
        logger.error(
            "Failed to send welcome to thread %s: %s",
            thread_id,
            e,
        )


async def _safe_process_ai_request(cmd: command_router.CommandEvent) -> None:
    """
    Process an AI command (mention, /ask, /imagine) and send the result.

    This is a fire-and-forget task — the webhook handler returns 200 OK
    before this function even starts the AI call. This ensures Meta's
    20-second timeout is never violated regardless of Gemini latency.

    The entire body is wrapped in try/except to prevent unhandled errors
    in fire-and-forget tasks from crashing the event loop or producing
    unhandled exception warnings.
    """
    try:
        if cmd.type in (CommandType.MENTION, CommandType.ASK):
            # Text command — send to Gemini for a Shadow System response
            result = await ai_engine.ask_gemini(cmd.text)
            await bot.send_text_reply(cmd.thread_id, result)

        elif cmd.type == CommandType.IMAGINE:
            # Image command — build Pollinations URL and send as attachment.
            # No actual image download happens here — Meta fetches it from the URL.
            url = ai_engine.generate_image_url(cmd.text)
            await bot.send_image_message(cmd.thread_id, url)

    except Exception as e:
        logger.error(
            "AI request failed — type=%s, sender=%s, thread=%s, error=%s: %s",
            cmd.type.value,
            cmd.sender_id,
            cmd.thread_id,
            type(e).__name__,
            e,
        )


@app.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring and load balancers."""
    return {
        "status": "alive",
        "service": "shadow-system-bot",
        "version": "2.0.0",
    }
