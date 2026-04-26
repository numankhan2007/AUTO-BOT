# ── cooldown.py — Per-User AI Request Rate Limiter ──
# Prevents AI API abuse by enforcing a configurable cooldown window
# between requests from the same sender.
#
# Strategy: Simple in-memory dict mapping sender_id → last request timestamp.
# Users on cooldown are silently ignored (no wasted Meta API calls for
# "cooldown active" messages — cleaner and more efficient).
#
# Memory management: cleanup_expired() is called by APScheduler every hour
# to remove stale entries and prevent unbounded dict growth in long-running
# processes. Entries older than 2x the cooldown window are removed since
# they will never trigger a cooldown check again.

import time
import logging

import config

logger = logging.getLogger("shadow-bot")

# Module-level in-memory store — persists for the lifetime of the process.
# This is intentionally NOT a database — cooldown state is ephemeral and
# acceptable to lose on restart (users just get one extra free request).
_last_request: dict[str, float] = {}


def is_on_cooldown(sender_id: str) -> bool:
    """
    Check if a sender is within their cooldown window.

    Returns True if the sender made an AI request less than
    AI_COOLDOWN_SECONDS ago. Returns False for first-time requesters
    (not in the dict) — everyone gets their first request free.

    Args:
        sender_id: The Instagram sender ID from the webhook payload.

    Returns:
        True if the sender should be rate-limited, False if they can proceed.
    """
    last_time = _last_request.get(sender_id)
    if last_time is None:
        # First request from this sender — not on cooldown
        return False

    elapsed = time.time() - last_time
    on_cooldown = elapsed < config.AI_COOLDOWN_SECONDS

    if on_cooldown:
        logger.debug(
            "Cooldown active for sender %s — %.1fs remaining",
            sender_id,
            config.AI_COOLDOWN_SECONDS - elapsed,
        )

    return on_cooldown


def record_request(sender_id: str) -> None:
    """
    Record that a sender has made an AI request right now.

    Called BEFORE the AI request is dispatched (not after) so that
    rapid duplicate clicks are caught even if the first request
    is still processing.

    Args:
        sender_id: The Instagram sender ID from the webhook payload.
    """
    _last_request[sender_id] = time.time()
    logger.debug("Cooldown recorded for sender %s", sender_id)


def cleanup_expired() -> int:
    """
    Remove cooldown entries that are older than 2x the cooldown window.

    Entries older than 2x AI_COOLDOWN_SECONDS are guaranteed to never
    trigger a cooldown check again, so they're safe to remove.
    The 2x multiplier provides a safety margin.

    Called by APScheduler every hour to prevent unbounded memory growth
    in long-running processes (e.g., a bot running for months).

    Returns:
        The number of entries removed (for logging by the caller).
    """
    now = time.time()
    # The threshold is 2x the cooldown to provide margin — an entry at exactly
    # 1x the cooldown might still be relevant for the current second's check
    cutoff = now - (config.AI_COOLDOWN_SECONDS * 2)

    # Build list of expired keys first to avoid modifying dict during iteration
    expired_keys = [
        sender_id
        for sender_id, timestamp in _last_request.items()
        if timestamp < cutoff
    ]

    for key in expired_keys:
        del _last_request[key]

    if expired_keys:
        logger.info(
            "Cooldown cleanup — removed %d expired entries, %d active",
            len(expired_keys),
            len(_last_request),
        )

    return len(expired_keys)
