"""
server/omni_recognizer.py — NVIDIA Nemotron VL (on AWS Bedrock) sign reader.

This is the OMNI EVAL BEAT (not the live recognizer). It sends a few sampled
frames of someone signing to NVIDIA's Nemotron-Nano-12B-v2-VL vision-language
model hosted on AWS Bedrock (us-west-2), and asks it to name the sign. We run it
SIDE-BY-SIDE against the on-device MediaPipe recognizer and score both in Cekura
— the "we used an open NVIDIA multimodal model on AWS + measured it" story.

NOT on the live demo critical path: VL on ASL is unproven, so MediaPipe stays the
spine. This endpoint exists for the comparison/eval, behind a config flag.

Env (already in .env):
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION=us-west-2
  NEMOTRON_VL_MODEL=nvidia.nemotron-nano-12b-v2

Run the FastAPI eval server:  uv run python omni_recognizer.py   (port 8788)
  POST /recognize-omni  { "frames": ["data:image/jpeg;base64,...", ...] }
    -> { "model": "...", "sign": "APPOINTMENT", "raw": "...", "latency_ms": 1234 }
"""

import base64
import json
import os
import re
import time

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(override=True)

REGION = os.getenv("AWS_REGION", "us-west-2")
MODEL_ID = os.getenv("NEMOTRON_VL_MODEL", "nvidia.nemotron-nano-12b-v2")
MAX_IMAGES = 4  # the model supports up to 4 high-res images

SIGN_PROMPT = (
    "These frames show a person communicating in American Sign Language. "
    "Identify the single sign or fingerspelled word being formed. "
    "Reply with ONLY the word in uppercase, nothing else. "
    "If unsure, reply UNKNOWN."
)


def _client():
    # Credentials are picked up from env (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION).
    return boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        config=Config(retries={"max_attempts": 2, "mode": "standard"}, read_timeout=30),
    )


def _strip_data_url(s: str) -> bytes:
    """Accept either a raw base64 string or a data: URL; return raw image bytes."""
    if s.startswith("data:"):
        s = s.split(",", 1)[1]
    return base64.b64decode(s)


def _build_body(frames: list[str]) -> dict:
    """OpenAI-style chat payload with image_url blocks — the shape NVIDIA's
    Bedrock VL models accept. We keep base64 data URLs so no S3 round-trip."""
    content = [{"type": "text", "text": SIGN_PROMPT}]
    for f in frames[:MAX_IMAGES]:
        # normalize to a data URL
        url = f if f.startswith("data:") else f"data:image/jpeg;base64,{f}"
        content.append({"type": "image_url", "image_url": {"url": url}})
    return {
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 16,
        "temperature": 0.2,
    }


def _extract_text(payload: dict) -> str:
    """Robustly pull the assistant text out of a Bedrock/OpenAI-style response."""
    # OpenAI-style
    try:
        return payload["choices"][0]["message"]["content"]
    except Exception:
        pass
    # some Bedrock wrappers nest differently
    for key in ("output", "outputs", "generation", "completion"):
        v = payload.get(key)
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for k2 in ("text", "content", "message"):
                if isinstance(v.get(k2), str):
                    return v[k2]
    return json.dumps(payload)[:200]


def recognize(frames: list[str]) -> dict:
    """Send sampled signing frames to Nemotron VL on Bedrock; return the sign guess."""
    if not frames:
        return {"model": MODEL_ID, "sign": "UNKNOWN", "raw": "", "latency_ms": 0, "error": "no frames"}
    body = _build_body(frames)
    t0 = time.time()
    try:
        resp = _client().invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(resp["body"].read())
        raw = _extract_text(payload).strip()
        # first all-caps word is the sign
        m = re.search(r"[A-Z][A-Z\-']{1,}", raw.upper())
        sign = m.group(0) if m else (raw.split()[0].upper() if raw else "UNKNOWN")
        return {
            "model": MODEL_ID,
            "sign": sign,
            "raw": raw,
            "latency_ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {
            "model": MODEL_ID,
            "sign": "UNKNOWN",
            "raw": "",
            "latency_ms": int((time.time() - t0) * 1000),
            "error": str(e),
        }


# ── tiny FastAPI eval server (so the client / eval harness can POST frames) ──
def _serve():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    class Req(BaseModel):
        frames: list[str]

    @app.get("/health")
    def health():
        return {"ok": True, "model": MODEL_ID, "region": REGION}

    @app.post("/recognize-omni")
    def recognize_omni(req: Req):
        return recognize(req.frames)

    print(f"OMNI eval server on http://localhost:8788  model={MODEL_ID} region={REGION}")
    uvicorn.run(app, host="0.0.0.0", port=8788, log_level="warning")


if __name__ == "__main__":
    import sys

    if "--serve" in sys.argv:
        _serve()
    else:
        # smoke test: no frames -> graceful; 1x1 px -> exercises the Bedrock call
        print("no-frames:", recognize([]))
        px = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pdwAAAAAElFTkSuQmCC"
        print("1px-call:", recognize([px]))
