
import os, requests, json

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

def ollama_chat(prompt: str, system: str | None = None, model: str | None = None) -> str:
    model = model or DEFAULT_MODEL
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system or "You are a concise, helpful assistant.",
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns { "response": "...", ... }
        return data.get("response", "").strip()
    except Exception as e:
        return f"[Ollama error: {e}. Is Ollama running and is the model pulled?]"
