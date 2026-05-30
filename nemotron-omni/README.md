# Nemotron 3 Nano Omni via OpenRouter

The fast path: NVIDIA Nemotron 3 Nano Omni (multimodal, 256K context) served by
OpenRouter — no GPU, no AWS quota, no deploy. The `:free` tier costs nothing.

## Why OpenRouter instead of self-hosting

Self-hosting this model needs an L40S-class GPU running vLLM. On AWS that meant a
`g6e` instance, which was blocked twice on the hackathon account: first by the
new **Free Plan** instance-type restriction (no paid EC2 types), then by a
**`ml.g6e` SageMaker endpoint quota of 0**. OpenRouter sidesteps both — it's just
an API key.

## Setup

```bash
cd nemotron-omni
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Get a key at https://openrouter.ai/keys and paste it into .env
```

## Usage

Text:
```bash
python client.py
```

Image (multimodal — the reason to use this model):
```bash
python example_image.py                       # uses a sample image
python example_image.py /path/to/photo.jpg     # your own image
python example_image.py /path/to/photo.jpg "What text is in this image?"
```

In your own code:
```python
from client import ask

ask("Summarize this contract clause: ...")
ask("What's in this image?", image_urls=["https://example.com/img.png"])
```

## Key facts

- **Model ID:** `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`
- **Base URL:** `https://openrouter.ai/api/v1` (OpenAI-compatible)
- **Context:** 256K tokens
- **Modalities:** text + image in, text out
- **Free tier:** ~21.8B weekly tokens, no per-minute limit documented

## Quick curl test (no Python)

```bash
curl -s -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
       "messages":[{"role":"user","content":"Say hello in one sentence."}],
       "max_tokens":100}'
```

## Migrating to self-hosted later

Because OpenRouter is OpenAI-compatible, the same `client.py` works against a
self-hosted vLLM endpoint — just change `BASE_URL` to your server and `MODEL` to
`nemotron`. Nothing else changes.
