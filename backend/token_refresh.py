# ── token_refresh.py — Meta Token Lifecycle Manager ──
# Handles short→long-lived token exchange, periodic refresh, and .env persistence.
#
# Token types in Meta's system:
# 1. Short-lived: ~1 hour, obtained from Graph API Explorer
# 2. Long-lived: ~60 days, exchanged from short-lived via /oauth/access_token
# 3. Never-expiring: Page tokens derived from long-lived user tokens (for pages you manage)
#
# This module handles type 2→2 refreshes on a 50-day cycle via APScheduler.

import os
import logging
import httpx
import config

logger = logging.getLogger("shadow-bot")

# Path to the .env file — same directory as this script
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


async def exchange_for_long_lived_token(short_lived_token: str) -> str:
    """
    Exchange a short-lived user token for a long-lived token (~60 days).

    This is a ONE-TIME operation. Run it manually after getting a token
    from Graph API Explorer:

        python -c "
        import asyncio
        from token_refresh import exchange_for_long_lived_token
        token = asyncio.run(exchange_for_long_lived_token('YOUR_SHORT_LIVED_TOKEN'))
        print(f'Long-lived token: {token}')
        "

    After running, paste the output token into your .env as PAGE_ACCESS_TOKEN.
    """
    url = f"{config.GRAPH_API_BASE}/oauth/access_token"

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config.INSTAGRAM_ACCOUNT_ID,  # Your App ID (not Instagram account)
        "client_secret": config.APP_SECRET,
        "fb_exchange_token": short_lived_token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        new_token = data.get("access_token")

        if not new_token:
            raise ValueError(f"No access_token in response: {data}")

        logger.info(
            "✅ Exchanged short-lived token for long-lived token (expires_in=%s)",
            data.get("expires_in", "unknown"),
        )
        return new_token


async def refresh_long_lived_token() -> None:
    """
    Refresh the current long-lived token before it expires.

    Called automatically by APScheduler every TOKEN_REFRESH_DAYS (default: 50).
    Long-lived tokens can be refreshed as long as they haven't expired yet.

    Flow:
    1. Call /oauth/access_token with the CURRENT long-lived token
    2. Receive a NEW long-lived token with a fresh 60-day expiry
    3. Persist the new token to .env (atomic write)
    4. Update config.PAGE_ACCESS_TOKEN in memory (hot reload)
    """
    url = f"{config.GRAPH_API_BASE}/oauth/access_token"

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config.INSTAGRAM_ACCOUNT_ID,
        "client_secret": config.APP_SECRET,
        "fb_exchange_token": config.PAGE_ACCESS_TOKEN,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            new_token = data.get("access_token")

            if not new_token:
                logger.error("Token refresh response missing access_token: %s", data)
                return

            # Persist to .env file (atomic write)
            _update_env_token(new_token)

            # Hot-reload in memory so the running process uses the new token immediately
            config.PAGE_ACCESS_TOKEN = new_token

            logger.info(
                "✅ Token refreshed successfully — expires_in=%s days",
                int(data.get("expires_in", 0)) // 86400,
            )

    except httpx.HTTPStatusError as e:
        logger.error(
            "❌ Token refresh failed — status=%d, body=%s",
            e.response.status_code,
            e.response.text,
        )
    except Exception as e:
        logger.error("❌ Token refresh unexpected error: %s", e)


def _update_env_token(new_token: str) -> None:
    """
    Atomically update PAGE_ACCESS_TOKEN in the .env file.

    Strategy:
    1. Read all existing lines
    2. Replace the PAGE_ACCESS_TOKEN line
    3. Write back atomically (write to temp, then rename)

    If the .env file doesn't exist or PAGE_ACCESS_TOKEN isn't in it,
    the token is appended as a new line.
    """
    try:
        # Read existing .env content
        if os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []

        # Find and replace the PAGE_ACCESS_TOKEN line
        found = False
        for i, line in enumerate(lines):
            if line.startswith("PAGE_ACCESS_TOKEN="):
                lines[i] = f'PAGE_ACCESS_TOKEN="{new_token}"\n'
                found = True
                break

        # If not found, append it
        if not found:
            lines.append(f'PAGE_ACCESS_TOKEN="{new_token}"\n')

        # Atomic write: write to .env.tmp, then rename to .env
        tmp_path = _ENV_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(tmp_path, _ENV_PATH)  # os.replace is atomic on POSIX

        logger.info("✅ .env updated with new PAGE_ACCESS_TOKEN")

    except OSError as e:
        logger.error("❌ Failed to update .env file: %s", e)
        raise
