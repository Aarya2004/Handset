"""
server/handset_bot.py — HANDSET bot (H1 gate: real Gradium TTS, local playback).

The real version of Arav's bridge_server.py say()-placeholder. Same WS schema, but
the verbatim/conduct text is spoken with GRADIUM TTS (the sponsor's voice), played
locally for now. Next step swaps local playback for a Twilio call to Aarya's phone.

Flow (Arav's schema, unchanged so recognizer.js drops in):
  client -> bot:  {type:"sign", token, text, mode:"verbatim"|"conduct"}
  bot   -> client:{type:"spoken", text}            (conduct echoes the sentence)
                  {type:"caption", speaker:"aarya", text}   (hearing reply; later)

  verbatim -> speak `text` (fixed string, NO LLM)         — the hero path
  conduct  -> Nemotron expands tokens -> sentence -> speak — the agent path
              (copied verbatim from Arav's proven bridge_server.py)

Run:  uv run python handset_bot.py        (WS on ws://localhost:8787/signal)
Test: open the Handset client, or POST a sign via the /say debug route.
"""

import asyncio
import base64
import json
import os
import subprocess
import tempfile
import wave

import httpx
import uvicorn
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

load_dotenv(override=True)

# ── Gradium TTS (sponsor voice) ──────────────────────────────────────────────
GRADIUM_URL = "wss://api.gradium.ai/api/speech/tts"
GRADIUM_KEY = os.environ["GRADIUM_API_KEY"]
GRADIUM_VOICE = os.getenv("GRADIUM_VOICE_ID", "Eu9iL_CYe8N-Gkx_")
TTS_SAMPLE_RATE = 48000

# ── Nemotron conduct (copied from Arav's proven bridge_server.py) ─────────────
NEMOTRON_URL = os.getenv(
    "NEMOTRON_LLM_URL",
    "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1",
).rstrip("/") + "/chat/completions"
NEMOTRON_MODEL = os.getenv("NEMOTRON_LLM_MODEL", "nvidia/nemotron-3-super")
CONDUCT_SYSTEM = (
    "You convert a Deaf caller's recognized ASL sign tokens into ONE short, natural, "
    "polite sentence spoken aloud to a receptionist. Fingerspelled letters may have "
    "errors; fix them from context. Reply with ONLY the sentence. "
    "Example: Tokens: HELLO, REFILL, M,E,D -> Hi, I'd like to refill my medication."
)

# Fixed verbatim phrases (hero path — mirrors Arav's client/bridge PHRASE map)
PHRASE = {
    "HELLO": "Hi there.",
    "APPOINTMENT": "Hi, I'd like to book an appointment.",
    "THURSDAY": "Thursday works for me.",
    "THANK-YOU": "Thank you so much.",
    "YES": "Yes, that works.",
    "NO": "No, thank you.",
    "CANCEL": "I'd like to cancel that.",
    "WAIT": "One moment, please.",
    "REPEAT": "Could you repeat that?",
    "WATER": "water",
}

app = FastAPI()
clients: set[WebSocket] = set()


async def broadcast(obj: dict):
    dead = []
    for c in list(clients):
        try:
            await c.send_text(json.dumps(obj))
        except Exception:
            dead.append(c)
    for d in dead:
        clients.discard(d)


# ── conduct: Nemotron turns noisy sign tokens into a real sentence ────────────
async def conduct(intent: str) -> str:
    payload = {
        "model": NEMOTRON_MODEL,
        "messages": [
            {"role": "system", "content": CONDUCT_SYSTEM},
            {"role": "user", "content": f"Tokens: {intent}"},
        ],
        "max_tokens": 64,
        "temperature": 0.3,
        "chat_template_kwargs": {"enable_thinking": False},  # mandatory for voice
    }
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(NEMOTRON_URL, json=payload)
            txt = (r.json()["choices"][0]["message"].get("content") or "").strip()
            return txt or intent
    except Exception as e:
        print(f"[conduct] Nemotron failed, raw intent: {e}")
        return intent


# ── Gradium TTS: text -> PCM bytes (48k mono) ─────────────────────────────────
async def gradium_tts(text: str) -> bytes:
    pcm = bytearray()
    req_id = "handset"
    headers = {"x-api-key": GRADIUM_KEY, "x-api-source": "handset"}
    async with websockets.connect(GRADIUM_URL, additional_headers=headers) as ws:
        await ws.send(json.dumps({"type": "setup", "voice_id": GRADIUM_VOICE, "client_req_id": req_id}))
        await ws.send(json.dumps({"type": "text", "text": text, "client_req_id": req_id}))
        await ws.send(json.dumps({"type": "end_of_stream", "client_req_id": req_id}))
        async for message in ws:
            msg = json.loads(message)
            t = msg.get("type")
            if t == "audio":
                pcm.extend(base64.b64decode(msg["audio"]))
            elif t == "end_of_stream":
                break
            elif t == "error":
                print(f"[gradium] error: {msg}")
                break
    return bytes(pcm)


def play_pcm_local(pcm: bytes):
    """Local playback of Gradium PCM (H1). Replaced by Twilio injection next step."""
    if not pcm:
        return
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit PCM
        w.setframerate(TTS_SAMPLE_RATE)
        w.writeframes(pcm)
    subprocess.Popen(["afplay", path])  # macOS local play


async def speak(text: str):
    """The seam that becomes 'inject into the Twilio call' later. For now: local."""
    print(f"[speak] {text!r}")
    pcm = await gradium_tts(text)
    play_pcm_local(pcm)


# ── WS endpoint: Arav's schema ────────────────────────────────────────────────
@app.websocket("/signal")
async def signal(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    await ws.send_text(json.dumps({"type": "bridge", "status": "connected"}))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("type") == "sign":
                mode = msg.get("mode", "verbatim")
                raw = (msg.get("token") or "").strip()
                if mode == "conduct":
                    text = await conduct(raw or msg.get("text") or "")
                    await speak(text)
                    await broadcast({"type": "spoken", "text": text})  # YOU caption
                else:  # verbatim (hero path, no LLM)
                    text = msg.get("text") or PHRASE.get(raw.upper(), raw.lower())
                    await speak(text)
                    await broadcast({"type": "spoken", "text": text})
            elif msg.get("type") == "hearing":  # test hook: simulate the phone reply
                await broadcast({"type": "caption", "speaker": "aarya", "text": msg.get("text", "")})
    except WebSocketDisconnect:
        clients.discard(ws)
    except Exception as e:
        print(f"[ws] {e}")
        clients.discard(ws)


# ── debug HTTP route so we can prove the H1 gate WITHOUT the client ───────────
@app.get("/say")
async def say(text: str = "Hi, I'd like to book an appointment.", mode: str = "verbatim", token: str = ""):
    """H1 button-proof: GET /say?text=...  or  /say?mode=conduct&token=APPOINTMENT,T,H,U,R,S,D,A,Y"""
    if mode == "conduct":
        text = await conduct(token or text)
    await speak(text)
    await broadcast({"type": "spoken", "text": text})
    return {"spoken": text, "mode": mode}


@app.get("/health")
def health():
    return {"ok": True, "clients": len(clients), "tts": "gradium", "voice": GRADIUM_VOICE}


if __name__ == "__main__":
    # NOTE: 8787 is taken by the Quorus MCP server — bot lives on 8790.
    print("HANDSET bot (H1: Gradium TTS, local playback) on ws://localhost:8790/signal")
    print("  prove it:  curl 'http://localhost:8790/say?text=Hello%20there'")
    print("  conduct :  curl 'http://localhost:8790/say?mode=conduct&token=APPOINTMENT,T,H,U,R,S,D,A,Y'")
    uvicorn.run(app, host="0.0.0.0", port=8790, log_level="warning")
