"""
SIGNAL ROOM — sign->speech bridge (H1, no-keys local proof).

The Signal Room browser client opens a WebSocket here and sends recognized
sign tokens. We "speak" them — for now via macOS `say` as a stand-in for the
real Twilio TTS leg, so the whole input->speech loop works with ZERO keys.

When keys land, the `speak()` function becomes: inject a TTSSpeakFrame into the
live Pipecat pipeline that's bridged to a Twilio call to Aarya. Same WS contract.

Run:  uv run python bridge_server.py     (from handset/server, deps already synced)
Then open the client at http://localhost:5050
"""

import asyncio
import json
import subprocess

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# Canonical verbatim phrases for the demo vocab (the "hero" path — no LLM).
# Mirrors PHRASE in client/index.html. The agent CONDUCTS, so a one-word sign
# becomes a natural spoken sentence.
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


def speak(text: str):
    """Placeholder TTS = macOS `say`. Swap for Pipecat TTSSpeakFrame->Twilio."""
    # non-blocking; -r 184 ~ natural rate
    subprocess.Popen(["say", "-r", "184", text])


@app.websocket("/signal")
async def signal(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    await ws.send_text(json.dumps({"type": "bridge", "status": "connected"}))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            kind = msg.get("type")
            if kind == "sign":
                token = (msg.get("token") or "").upper()
                text = msg.get("text") or PHRASE.get(token, token.lower())
                speak(text)
                await broadcast({"type": "spoken", "text": text})
            elif kind == "hearing":
                # test hook: inject what the hearing party said -> caption
                await broadcast({"type": "caption", "speaker": "aarya", "text": msg.get("text", "")})
    except WebSocketDisconnect:
        clients.discard(ws)
    except Exception:
        clients.discard(ws)


@app.get("/health")
def health():
    return {"ok": True, "clients": len(clients)}


if __name__ == "__main__":
    print("SIGNAL ROOM bridge on ws://localhost:8787/signal  (say-TTS placeholder)")
    uvicorn.run(app, host="0.0.0.0", port=8787, log_level="warning")
