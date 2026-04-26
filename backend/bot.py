# ── bot.py — Instagram Group Chat Bot Logic ──
# Handles webhook payload parsing and welcome message delivery.
# Supports BOTH messaging[] and changes[] payload formats from Meta.

import logging
import httpx
import config

logger = logging.getLogger("shadow-bot")

# ── Welcome Message ──
# EXACT text from src/data/prompt.js — the 7 commandments.
# This is the source of truth for the welcome message payload.
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


def parse_member_added_event(payload: dict) -> list[dict]:
    """
    Parse a Meta webhook payload for member_added events.

    Meta sends Instagram webhook events in two possible formats:
    1. `entry[].messaging[]` — Direct messaging events (DMs, group messages)
    2. `entry[].changes[]` — Subscription-based changes (page, instagram, etc.)

    For Instagram group thread `member_added` events, Meta uses the messaging[]
    format where each messaging item has an `event` field set to "member_added".

    Returns a list of dicts with shape:
        [{ "thread_id": str, "member_ids": list[str] }]
    """
    results = []

    for entry in payload.get("entry", []):
        # ── Format 1: messaging[] (primary for Instagram thread events) ──
        # Each messaging item looks like:
        # {
        #   "sender": {"id": "..."},
        #   "recipient": {"id": "..."},
        #   "timestamp": 1234567890,
        #   "event": "member_added",
        #   "thread_id": "t_xxxx",         ← the group thread ID
        #   "members": [{"id": "..."}]      ← newly added members
        # }
        for msg in entry.get("messaging", []):
            event_type = msg.get("event", "")

            if event_type == "member_added":
                thread_id = msg.get("thread_id")
                # member IDs live in the "members" array, each with an "id" key
                member_ids = [m.get("id") for m in msg.get("members", []) if m.get("id")]

                if thread_id and member_ids:
                    results.append({
                        "thread_id": thread_id,
                        "member_ids": member_ids,
                    })
                    logger.info(
                        "member_added detected — thread=%s, members=%s",
                        thread_id,
                        member_ids,
                    )

        # ── Format 2: changes[] (fallback — Meta may use this for some event types) ──
        # {
        #   "field": "messages",
        #   "value": {
        #     "event": "member_added",
        #     "thread_id": "t_xxxx",
        #     "members": [{"id": "..."}]
        #   }
        # }
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("event") == "member_added":
                thread_id = value.get("thread_id")
                member_ids = [m.get("id") for m in value.get("members", []) if m.get("id")]

                if thread_id and member_ids:
                    results.append({
                        "thread_id": thread_id,
                        "member_ids": member_ids,
                    })
                    logger.info(
                        "member_added (changes format) — thread=%s, members=%s",
                        thread_id,
                        member_ids,
                    )

    return results


async def send_welcome_message(thread_id: str) -> dict:
    """
    POST the welcome message to the specified Instagram group thread.

    Uses Meta Graph API v19.0 endpoint: POST /me/messages
    The bot MUST be an admin of the group thread for this to succeed.

    Rate limits: Meta allows ~200 API calls per hour per Page.
    We send one message per member_added event, so this is well within limits.

    Returns the API response dict on success.
    Raises httpx.HTTPStatusError on API failure (logged, not silenced).
    """
    url = f"{config.GRAPH_API_BASE}/me/messages"

    # Meta messaging API payload structure:
    # - recipient.thread_key: the group thread identifier
    # - message.text: the message body (plain text, supports emoji)
    payload = {
        "recipient": {"thread_key": thread_id},
        "message": {"text": WELCOME_MESSAGE},
        "access_token": config.PAGE_ACCESS_TOKEN,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            logger.info(
                "✅ Welcome message sent — thread=%s, message_id=%s",
                thread_id,
                data.get("message_id", "unknown"),
            )
            return data
        else:
            # Log the full error for debugging — Meta returns descriptive error bodies
            logger.error(
                "❌ Failed to send welcome message — thread=%s, status=%d, body=%s",
                thread_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()


async def send_text_reply(thread_id: str, text: str) -> dict:
    """
    Send a dynamic text reply to the specified Instagram group thread.

    Same structure as send_welcome_message() but accepts arbitrary text
    instead of using the fixed WELCOME_MESSAGE. Used for AI-generated
    responses from Gemini (Shadow System persona).

    Args:
        thread_id: The group thread identifier from the webhook payload.
        text: The AI-generated response text to send.

    Returns:
        The API response dict on success.
    """
    url = f"{config.GRAPH_API_BASE}/me/messages"

    payload = {
        "recipient": {"thread_key": thread_id},
        "message": {"text": text},
        "access_token": config.PAGE_ACCESS_TOKEN,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            logger.info(
                "✅ AI text reply sent — thread=%s, message_id=%s, length=%d",
                thread_id,
                data.get("message_id", "unknown"),
                len(text),
            )
            return data
        else:
            logger.error(
                "❌ Failed to send AI text reply — thread=%s, status=%d, body=%s",
                thread_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()


async def send_image_message(thread_id: str, image_url: str) -> dict:
    """
    Send an image attachment to the specified Instagram group thread.

    Uses Meta's image attachment payload format. The image_url points to
    a Pollinations.ai URL which is publicly accessible — Meta's servers
    will fetch the image directly from that URL when delivering the message.

    Meta API assumption: The Graph API accepts external URLs in the
    attachment payload.url field. The URL must be publicly reachable
    by Meta's servers (Pollinations URLs are persistent and public).

    is_reusable=True tells Meta to cache the attachment for future sends,
    reducing latency if the same image URL is used again.

    Args:
        thread_id: The group thread identifier from the webhook payload.
        image_url: The publicly accessible URL of the image to send.

    Returns:
        The API response dict on success.
    """
    url = f"{config.GRAPH_API_BASE}/me/messages"

    # Meta image attachment payload structure:
    # - attachment.type: "image" for image attachments
    # - attachment.payload.url: public URL Meta's servers will fetch
    # - attachment.payload.is_reusable: cache the attachment on Meta's side
    payload = {
        "recipient": {"thread_key": thread_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True,
                },
            },
        },
        "access_token": config.PAGE_ACCESS_TOKEN,
    }

    logger.info("Sending image to thread=%s — url=%s", thread_id, image_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            logger.info(
                "✅ Image message sent — thread=%s, message_id=%s",
                thread_id,
                data.get("message_id", "unknown"),
            )
            return data
        else:
            logger.error(
                "❌ Failed to send image message — thread=%s, status=%d, body=%s",
                thread_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()

