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
from typing import Any

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(override=True)

REGION = os.getenv("AWS_REGION", "us-west-2")
MODEL_ID = os.getenv("NEMOTRON_VL_MODEL", "nvidia.nemotron-nano-12b-v2")
MAX_IMAGES = int(os.getenv("NEMOTRON_VL_MAX_IMAGES", "4"))

# The demo sign vocabulary the VLM chooses from. Multiple-choice prompting is
# what makes the VLM actually work: open-ended "identify the sign" returns
# UNKNOWN, but "which of these is it?" with a candidate list succeeds (verified
# live — an open-hand sign was correctly read as a wave).
DEFAULT_VOCAB = [
    "HELLO", "YES", "NO", "THANK-YOU", "APPOINTMENT", "CANCEL", "WAIT", "REPEAT", "WATER",
]

SIGN_HINTS = {
    "HELLO": "open hand near the face or head, often with a small wave",
    "YES": "closed fist nods up and down like a head nod",
    "NO": "index and middle finger close against the thumb",
    "THANK-YOU": (
        "flat open hand starts at the chin or lips, then moves outward/forward away from "
        "the face; if the final frame looks like an open HELLO hand but earlier frames "
        "show it leaving the mouth/chin, choose THANK-YOU"
    ),
    "APPOINTMENT": "index fingers or hands meet/mark a scheduled point in front of the body",
    "CANCEL": "hands cross or cut/stop the current action",
    "WAIT": "open hands held up with fingers wiggling or pausing",
    "REPEAT": "one hand points or taps back toward the other hand to ask again",
    "WATER": "W handshape taps near the chin",
}


def _sign_prompt(vocab: list[str]) -> str:
    options = ", ".join(vocab) + ", UNKNOWN"
    hints = "\n".join(
        f"- {term}: {SIGN_HINTS[term]}"
        for term in vocab
        if term in SIGN_HINTS
    )
    return (
        "You are classifying ONE short American Sign Language sign from chronological video frames. "
        "The frames are ordered from earliest to latest; use the motion across frames, not only the final pose. "
        "Choose exactly one option from the allowed list, or UNKNOWN if the evidence is weak. "
        f"Allowed signs: {options}.\n"
        f"Sign cues:\n{hints}\n"
        "Return exactly two lines:\n"
        "SIGN: <CHOICE>\n"
        "CONFIDENCE: <0.00-1.00>"
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


def _build_body(frames: list[str], vocab: list[str]) -> dict:
    """OpenAI-style chat payload with image_url blocks — the shape NVIDIA's
    Bedrock VL models accept. We keep base64 data URLs so no S3 round-trip."""
    content: list[dict[str, Any]] = [{"type": "text", "text": _sign_prompt(vocab)}]
    for f in frames[:MAX_IMAGES]:
        # normalize to a data URL
        url = f if f.startswith("data:") else f"data:image/jpeg;base64,{f}"
        content.append({"type": "image_url", "image_url": {"url": url}})
    return {
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 32,
        "temperature": 0.0,
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


def _parse_sign(raw: str, vocab: list[str]) -> str:
    """Pull the chosen sign from the model's reply. Prefers the 'SIGN: X' line;
    falls back to the first vocab term that appears in the text."""
    up = raw.upper()
    m = re.search(r"SIGN:\s*([A-Z][A-Z\-']+)", up)
    if m:
        choice = m.group(1)
        allowed = {term.upper() for term in vocab} | {"UNKNOWN"}
        return choice if choice in allowed else "UNKNOWN"
    # fallback: any vocab term mentioned
    for term in vocab + ["UNKNOWN"]:
        if term.upper() in up:
            return term.upper()
    return "UNKNOWN"


def _parse_confidence(raw: str, sign: str) -> float:
    m = re.search(r"CONFIDENCE:\s*(0(?:\.\d+)?|1(?:\.0+)?)", raw.upper())
    if not m:
        return 0.0 if sign == "UNKNOWN" else 0.65
    try:
        return max(0.0, min(1.0, float(m.group(1))))
    except ValueError:
        return 0.0 if sign == "UNKNOWN" else 0.65


def recognize(frames: list[str], vocab: list[str] | None = None) -> dict:
    """Send sampled signing frames to Nemotron VL on Bedrock; return the sign guess."""
    vocab = vocab or DEFAULT_VOCAB
    if not frames:
        return {"model": MODEL_ID, "sign": "UNKNOWN", "raw": "", "latency_ms": 0, "error": "no frames"}
    body = _build_body(frames, vocab)
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
        sign = _parse_sign(raw, vocab)
        confidence = _parse_confidence(raw, sign)
        return {
            "model": MODEL_ID,
            "sign": sign,
            "confidence": confidence,
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
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    class Req(BaseModel):
        frames: list[str]
        vocab: list[str] | None = None

    @app.get("/health")
    def health():
        return {"ok": True, "model": MODEL_ID, "region": REGION}

    @app.post("/recognize-omni")
    def recognize_omni(req: Req):
        return recognize(req.frames, req.vocab)

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
