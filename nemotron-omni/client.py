"""Reusable Nemotron 3 Nano Omni client via OpenRouter.

OpenRouter exposes an OpenAI-compatible API, so we use the official `openai`
SDK pointed at OpenRouter's base URL. The model is fully multimodal (text +
image), so `ask` accepts an optional list of image URLs.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

# Load from this folder's .env if present, else fall back to the project's
# server/.env (where the key actually lives).
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "server", ".env"))

MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
BASE_URL = "https://openrouter.ai/api/v1"


def make_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add "
            "your key from https://openrouter.ai/keys"
        )
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def ask(prompt: str, image_urls: list[str] | None = None, **kwargs) -> str:
    """Send a prompt (optionally with images) and return the text reply.

    image_urls: list of http(s) URLs or data: URIs. Omit for text-only.
    """
    client = make_client()

    if image_urls:
        content = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})
        messages = [{"role": "user", "content": content}]
    else:
        messages = [{"role": "user", "content": prompt}]

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=kwargs.pop("max_tokens", 1024),
        # OpenRouter uses these for leaderboard attribution; harmless to send.
        extra_headers={
            "HTTP-Referer": "https://localhost",
            "X-Title": "nemotron-omni-hackathon",
        },
        **kwargs,
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    print(ask("In one sentence, what is NVIDIA Nemotron 3 Nano Omni?"))
