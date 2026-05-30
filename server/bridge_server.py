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

import httpx
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


# --- the AGENT path: Nemotron turns noisy sign tokens into a real sentence -----
NEMOTRON_URL = "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1/chat/completions"
CONDUCT_SYSTEM = (
    "You convert a Deaf caller's recognized ASL sign tokens into ONE short, natural, "
    "polite sentence spoken aloud to a receptionist. Fingerspelled letters may have "
    "errors; fix them from context. Reply with ONLY the sentence. "
    "Example: Tokens: HELLO, REFILL, M,E,D -> Hi, I'd like to refill my medication."
)
# Disambiguation variant: the recognizer was UNSURE, so it hands us its top guesses
# (with confidences) plus the live call context. Nemotron does the linguistic work
# the on-device k-NN can't: pick the most likely sign from context, then expand it.
DISAMBIGUATE_SYSTEM = (
    "You help a Deaf caller on a live phone call. Their on-device sign recognizer was "
    "UNSURE and gives you its top candidate signs (each with a confidence 0-1) plus the "
    "recent conversation. Choose the single most likely intended sign using the "
    "conversational context, then reply with ONE short, natural, polite sentence to speak "
    "aloud to a receptionist. Fingerspelled letters may have errors; fix them from context. "
    "Reply with ONLY the sentence.\n"
    "Example:\n"
    "Recent conversation: AARYA: Sure, what day works for you?\n"
    "Candidates: AFTERNOON (0.61), APPOINTMENT (0.58), AGAIN (0.41)\n"
    "-> The afternoon works for me."
)


def _format_candidates(candidates: list) -> str:
    """[["AFTERNOON", 0.61], ["APPOINTMENT", 0.58]] -> 'AFTERNOON (0.61), APPOINTMENT (0.58)'."""
    parts = []
    for c in candidates:
        if isinstance(c, (list, tuple)) and c:
            label = str(c[0])
            conf = f" ({float(c[1]):.2f})" if len(c) > 1 and c[1] is not None else ""
            parts.append(f"{label}{conf}")
        elif c:
            parts.append(str(c))
    return ", ".join(parts)


async def _nemotron(system: str, user: str, fallback: str) -> str:
    """One Nemotron chat call. Returns the reply text, or `fallback` on any error."""
    payload = {
        "model": "nvidia/nemotron-3-super",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 64,
        "temperature": 0.3,
        "chat_template_kwargs": {"enable_thinking": False},  # mandatory for voice
    }
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(NEMOTRON_URL, json=payload)
            txt = (r.json()["choices"][0]["message"].get("content") or "").strip()
            return txt or fallback
    except Exception as e:
        print(f"[nemotron] call failed, falling back to '{fallback}': {e}")
        return fallback


async def conduct(intent: str) -> str:
    """This is what makes us an AGENT, not a dumb relay: Nemotron expands +
    error-corrects the signed intent into natural speech. Verified on the live
    endpoint (Z,O,L,O,F,T -> 'I'd like to refill my Zoloft.')."""
    return await _nemotron(CONDUCT_SYSTEM, f"Tokens: {intent}", fallback=intent)


async def disambiguate(candidates: list, context: list | None = None) -> str:
    """The recognizer was unsure: Nemotron picks the most likely candidate from the
    live conversation context, then expands it into a natural spoken sentence. This is
    where NVIDIA does real linguistic work the on-device recognizer cannot."""
    cand_str = _format_candidates(candidates)
    ctx_lines = "\n".join(str(c) for c in (context or []) if c)
    user = (
        (f"Recent conversation:\n{ctx_lines}\n" if ctx_lines else "")
        + f"Candidates: {cand_str}"
    )
    # fallback = the recognizer's own top guess, lowercased, if Nemotron is unreachable
    top = candidates[0][0] if candidates and isinstance(candidates[0], (list, tuple)) else (candidates[0] if candidates else "")
    return await _nemotron(DISAMBIGUATE_SYSTEM, user, fallback=str(top).lower())


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
                mode = msg.get("mode", "verbatim")
                raw = msg.get("token") or ""
                if mode == "disambiguate":
                    # recognizer was unsure -> Nemotron picks from top candidates + context
                    text = await disambiguate(msg.get("candidates") or [], msg.get("context") or [])
                    speak(text)
                    await broadcast({"type": "spoken", "text": text})  # echo resolved sentence
                elif mode == "conduct":
                    text = await conduct(raw or msg.get("text") or "")
                    speak(text)
                    await broadcast({"type": "spoken", "text": text})  # conduct: echo the result
                else:
                    text = msg.get("text") or PHRASE.get(raw.upper(), raw.lower())
                    speak(text)  # verbatim: client already shows it optimistically
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
