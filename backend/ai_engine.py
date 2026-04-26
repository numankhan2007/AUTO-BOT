# ── ai_engine.py — Shadow System AI Engine ──
# Handles all AI-powered response generation:
#   - Text replies via Google Gemini 1.5 Flash
#   - Image generation URLs via Pollinations.ai (free, no auth)
#
# Design decisions:
#   - google-generativeai SDK is synchronous — we wrap it with asyncio.to_thread()
#     to prevent blocking the FastAPI event loop
#   - Pollinations.ai returns the image directly at the URL — no download needed,
#     Meta's servers fetch the image from the public URL when we send the attachment
#   - The Shadow System persona is injected via system_instruction in the model
#     constructor, NOT prepended to user messages (cleaner, uses API correctly)

import time
import logging
import asyncio
import urllib.parse

import google.generativeai as genai

import config

logger = logging.getLogger("shadow-bot")

# ── Shadow System Persona ──
# Embedded as system_instruction in the Gemini model constructor.
# This keeps the persona consistent across all requests without polluting user prompts.
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

# ── Gemini Model (Lazy Singleton) ──
# Initialized once on first use, not at import time, so the module can be
# imported safely even in test environments without a valid API key.
_model = None


def _get_model() -> genai.GenerativeModel:
    """Return the cached Gemini model instance, creating it on first call."""
    global _model
    if _model is None:
        # system_instruction tells Gemini to adopt the Shadow System persona
        # for every request — no need to repeat it in each user message
        _model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION,
        )
        logger.info("Gemini 2.5 Flash model initialized with Shadow System persona")
    return _model


async def ask_gemini(user_text: str) -> str:
    """
    Generate a text response from Gemini 1.5 Flash with the Shadow System persona.

    Uses asyncio.to_thread() because the google-generativeai SDK's generate_content()
    is synchronous — calling it directly would block the event loop and delay
    all other webhook processing (violating Meta's 20-second response window).

    Args:
        user_text: The cleaned user message (trigger prefix already stripped).

    Returns:
        The Shadow System's response text, or a styled fallback on error.
    """
    start = time.monotonic()
    # Truncate for logging — don't spam logs with full-length user messages
    log_preview = user_text[:100] + ("…" if len(user_text) > 100 else "")
    logger.info("Gemini request — input: %s", log_preview)

    try:
        model = _get_model()

        # Wrap the synchronous SDK call in a thread to keep the event loop free.
        # asyncio.to_thread() runs the callable in the default executor (thread pool).
        response = await asyncio.to_thread(
            model.generate_content, user_text
        )

        elapsed = time.monotonic() - start
        result_text = response.text

        logger.info(
            "Gemini response — %d chars in %.2fs",
            len(result_text),
            elapsed,
        )
        return result_text

    except Exception as e:
        # Never expose raw error details to the group chat — stay in character.
        # Log the full error for debugging, return a styled fallback.
        elapsed = time.monotonic() - start
        logger.error(
            "Gemini request failed after %.2fs — %s: %s",
            elapsed,
            type(e).__name__,
            e,
        )
        return "The System encountered interference. Try again, Hunter. ⚔️"


def generate_image_url(prompt: str) -> str:
    """
    Build a Pollinations.ai image URL from the given text prompt.

    Pollinations.ai is a free, no-auth image generation API. The URL IS the image —
    when accessed, it returns the generated image directly (no JSON wrapper).
    Meta's Graph API accepts external URLs for image attachments, and Pollinations
    URLs are persistent and publicly accessible, so Meta's servers can fetch them.

    This function is synchronous and instant — it only builds a URL string,
    no I/O or network calls are made.

    Args:
        prompt: The image description from the user (after stripping /imagine prefix).

    Returns:
        The fully constructed Pollinations image URL.
    """
    # URL-encode the prompt so special characters don't break the URL
    encoded_prompt = urllib.parse.quote(prompt, safe="")

    # Build the full URL with quality parameters:
    # - width/height: 1024x1024 for high-quality square images
    # - model=flux: Pollinations' best image model
    # - nologo=true: removes the Pollinations watermark
    # - enhance=true: applies prompt enhancement for better results
    url = (
        f"{config.POLLINATIONS_BASE_URL}/prompt/{encoded_prompt}"
        f"?width=1024&height=1024&model=flux&nologo=true&enhance=true"
    )

    logger.info("Pollinations URL constructed — %s", url)
    return url
