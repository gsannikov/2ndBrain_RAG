
import os
import logging
import requests
import json

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = 300  # 5 minutes


def ollama_chat(prompt: str, system: str | None = None, model: str | None = None) -> str:
    """
    Call Ollama API for chat completion.

    Args:
        prompt: User prompt/question
        system: Optional system prompt
        model: Optional model name (uses DEFAULT_MODEL if not specified)

    Returns:
        Response text from Ollama, or error message if request fails
    """
    model = model or DEFAULT_MODEL
    url = f"{OLLAMA_HOST}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system or "You are a concise, helpful assistant.",
        "stream": False
    }

    try:
        logger.debug(f"Calling Ollama: model={model}, prompt_len={len(prompt)}")

        resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)

        # Check for HTTP errors
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"Ollama HTTP error: {resp.status_code}")
            if resp.status_code == 404:
                return f"[Model not found: {model}. Did you pull it? (ollama pull {model})]"
            elif resp.status_code == 500:
                return "[Ollama server error. Check logs.]"
            else:
                return f"[HTTP {resp.status_code} from Ollama]"

        # Parse response
        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            return "[Error: Ollama returned invalid JSON]"

        # Extract response
        response_text = data.get("response", "").strip()
        if not response_text:
            logger.warning("Empty response from Ollama")
            return "[Ollama returned empty response]"

        logger.debug(f"Ollama response received ({len(response_text)} chars)")
        return response_text

    except requests.Timeout:
        logger.error(f"Ollama request timed out after {OLLAMA_TIMEOUT}s")
        return "[Request timed out. Ollama model took too long to respond.]"

    except requests.ConnectionError:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}")
        return f"[Cannot reach Ollama at {OLLAMA_HOST}. Is it running? (ollama serve)]"

    except requests.RequestException as e:
        logger.error(f"Ollama request error: {e}")
        return f"[Network error: {type(e).__name__}]"

    except Exception as e:
        logger.error(f"Unexpected error calling Ollama: {e}")
        return f"[Unexpected error: {type(e).__name__}]"
