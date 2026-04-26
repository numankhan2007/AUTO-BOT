# ── command_router.py — Message Event Parser & Command Detector ──
# Extracts text messages from Meta webhook payloads and classifies them
# as bot commands (mention, /ask, /imagine) or non-commands (discarded).
#
# Architecture:
#   parse_message_event() extracts raw messages from the payload (mirrors
#   the structure of parse_member_added_event() in bot.py).
#   detect_command() classifies each message into a typed CommandEvent.
#
# Self-reply prevention is the FIRST check in parse_message_event() —
# any message from the bot's own account ID is silently dropped before
# it can trigger command detection or AI calls.

import logging
from dataclasses import dataclass
from enum import Enum

import config

logger = logging.getLogger("shadow-bot")


class CommandType(Enum):
    """Types of commands the bot can respond to."""
    MENTION = "mention"    # @BotName <text>
    ASK = "ask"            # /ask <text>
    IMAGINE = "imagine"    # /imagine <description>
    NONE = "none"          # Not a bot command — silently discard


@dataclass
class CommandEvent:
    """A parsed, typed command ready for processing by the AI engine."""
    type: CommandType
    sender_id: str
    thread_id: str
    text: str  # Cleaned text with the trigger prefix stripped


def parse_message_event(payload: dict) -> list[dict]:
    """
    Parse a Meta webhook payload for text message events.

    Mirrors the structure of parse_member_added_event() in bot.py.
    Extracts messages from the messaging[] array where the item contains
    a "message" field with a "text" sub-field.

    Self-reply prevention: Messages where sender.id matches the bot's own
    INSTAGRAM_ACCOUNT_ID are dropped immediately. This prevents infinite
    loops where the bot responds to its own messages.

    Returns:
        List of dicts with shape: [{"sender_id": str, "thread_id": str, "text": str}]
    """
    results = []

    for entry in payload.get("entry", []):
        for msg in entry.get("messaging", []):
            # Only process items that contain a "message" object with text.
            # This filters out member_added events, read receipts, reactions, etc.
            message_obj = msg.get("message")
            if message_obj is None:
                continue

            text = message_obj.get("text")
            if not text or not text.strip():
                # Skip empty or whitespace-only messages — nothing to process
                continue

            sender_id = msg.get("sender", {}).get("id", "")
            # thread_id can come from the top-level "thread_id" field
            # or from the "recipient" object depending on Meta's payload format
            thread_id = msg.get("thread_id", "") or msg.get("recipient", {}).get("id", "")

            if not sender_id or not thread_id:
                logger.debug("Skipping message with missing sender_id or thread_id")
                continue

            # ── SELF-REPLY PREVENTION ──
            # This is the FIRST substantive check — drop messages from the bot itself
            # before any further processing. Prevents the bot from responding to
            # its own AI replies in an infinite loop.
            if sender_id == config.INSTAGRAM_ACCOUNT_ID:
                logger.debug("Dropping self-sent message from bot account %s", sender_id)
                continue

            results.append({
                "sender_id": sender_id,
                "thread_id": thread_id,
                "text": text.strip(),
            })

    logger.debug("Parsed %d text message(s) from webhook payload", len(results))
    return results


def detect_command(message: dict) -> CommandEvent:
    """
    Classify a parsed message as a bot command or a non-command.

    Trigger detection order:
      1. @BOT_USERNAME <text>  → CommandType.MENTION
      2. /ask <text>           → CommandType.ASK
      3. /imagine <text>       → CommandType.IMAGINE
      4. Anything else         → CommandType.NONE (silently discarded)

    The remaining text after stripping the trigger prefix is validated —
    if it's empty after stripping, the command is downgraded to NONE
    (e.g., someone just typing "@bot" with nothing after it).

    Args:
        message: Dict with keys "sender_id", "thread_id", "text"

    Returns:
        A CommandEvent with the classified type and cleaned text.
    """
    sender_id = message["sender_id"]
    thread_id = message["thread_id"]
    text = message["text"]

    # ── Check 1: @mention trigger ──
    # Case-insensitive comparison for the mention, since Instagram usernames
    # are case-insensitive and users may type @BOTname or @botname
    mention_prefix = f"@{config.BOT_USERNAME}"
    if text.lower().startswith(mention_prefix.lower()):
        # Strip the @username prefix and any leading whitespace from the remaining text
        remaining = text[len(mention_prefix):].strip()
        if remaining:
            logger.debug("MENTION command detected from sender %s", sender_id)
            return CommandEvent(
                type=CommandType.MENTION,
                sender_id=sender_id,
                thread_id=thread_id,
                text=remaining,
            )
        # Empty text after mention — nothing to process, treat as non-command
        logger.debug("Empty mention from sender %s — discarding", sender_id)
        return CommandEvent(type=CommandType.NONE, sender_id=sender_id, thread_id=thread_id, text="")

    # ── Check 2: /ask trigger ──
    # Case-insensitive prefix match — users may type /Ask, /ASK, etc.
    if text.lower().startswith("/ask "):
        remaining = text[5:].strip()  # len("/ask ") == 5
        if remaining:
            logger.debug("ASK command detected from sender %s", sender_id)
            return CommandEvent(
                type=CommandType.ASK,
                sender_id=sender_id,
                thread_id=thread_id,
                text=remaining,
            )
        logger.debug("Empty /ask from sender %s — discarding", sender_id)
        return CommandEvent(type=CommandType.NONE, sender_id=sender_id, thread_id=thread_id, text="")

    # ── Check 3: /imagine trigger ──
    if text.lower().startswith("/imagine "):
        remaining = text[9:].strip()  # len("/imagine ") == 9
        if remaining:
            logger.debug("IMAGINE command detected from sender %s", sender_id)
            return CommandEvent(
                type=CommandType.IMAGINE,
                sender_id=sender_id,
                thread_id=thread_id,
                text=remaining,
            )
        logger.debug("Empty /imagine from sender %s — discarding", sender_id)
        return CommandEvent(type=CommandType.NONE, sender_id=sender_id, thread_id=thread_id, text="")

    # ── No trigger matched — silently discard ──
    # Non-command messages are the vast majority of group chat traffic.
    # Logging at DEBUG to avoid flooding logs with every single group message.
    return CommandEvent(type=CommandType.NONE, sender_id=sender_id, thread_id=thread_id, text="")
