"""
server/handset_bot.py — HANDSET bot (H2: Gradium TTS → real Twilio phone call).

The bot has two modes controlled by HANDSET_LOCAL_AUDIO=1:
  - Default (HANDSET_LOCAL_AUDIO unset): signs are spoken onto a live Twilio call
    via a Pipecat pipeline (FastAPIWebsocketTransport + GradiumTTSService).
  - Fallback (HANDSET_LOCAL_AUDIO=1): original H1 behaviour — Gradium PCM piped
    to afplay locally.  This keeps the H1 gate path intact.

WS schema (unchanged, recognizer.js drops in unchanged):
  client -> bot:  {type:"sign", token, text, mode:"verbatim"|"conduct"}
  bot -> client:  {type:"spoken", text}
                  {type:"caption", speaker:"aarya", text}   (hearing reply; later)

  verbatim -> speak `text` (fixed string / PHRASE map, NO LLM)   — hero path
  conduct  -> Nemotron expands tokens -> sentence -> speak         — agent path

FastAPI routes:
  WS  /signal       — client sign-stream (port 8790, unchanged)
  WS  /twilio-media — Twilio bidirectional media stream (Pipecat pipeline endpoint)
  GET /call         — trigger an outbound call; requires PUBLIC_HOST query param
                      (or env var PUBLIC_HOST) pointing at the cloudflared tunnel
  GET /say          — debug: speak a phrase without a WS client
  GET /health       — liveness probe

Run sequence (full phone-call path):
  1. Start cloudflared:
       cloudflared tunnel --url http://localhost:8790
     Note the assigned hostname, e.g. https://xyz.trycloudflare.com

  2. Start the bot:
       uv run python handset_bot.py

  3. Trigger the call:
       curl 'http://localhost:8790/call?public_host=xyz.trycloudflare.com'
     Twilio calls TWILIO_TO_NUMBER; when it connects, the media stream opens
     /twilio-media and the Pipecat pipeline starts.  Signs sent on /signal are
     now spoken down the live phone call.
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
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from twilio.rest import Client as TwilioClient

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import TranscriptionFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.gradium.tts import GradiumTTSService
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.workers.runner import WorkerRunner

from lexicon import boost
from nvidia_stt import NVidiaWebSocketSTTService

load_dotenv(override=True)

# ── Feature flag ─────────────────────────────────────────────────────────────
# Set HANDSET_LOCAL_AUDIO=1 to keep the original H1 local-afplay path.
LOCAL_AUDIO = os.getenv("HANDSET_LOCAL_AUDIO", "").strip() == "1"

# ── Gradium TTS (sponsor voice) ──────────────────────────────────────────────
GRADIUM_URL = "wss://api.gradium.ai/api/speech/tts"
GRADIUM_KEY = os.environ["GRADIUM_API_KEY"]
GRADIUM_VOICE = os.getenv("GRADIUM_VOICE_ID", "Eu9iL_CYe8N-Gkx_")
TTS_SAMPLE_RATE = 48000

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_TO_NUMBER = os.getenv("TWILIO_TO_NUMBER", "")

# ── Nemotron conduct (copied from Arav's proven bridge_server.py) ─────────────
NEMOTRON_URL = os.getenv(
    "NEMOTRON_LLM_URL",
    "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1",
).rstrip("/") + "/chat/completions"
NEMOTRON_MODEL = os.getenv("NEMOTRON_LLM_MODEL", "nvidia/nemotron-3-super")
CONDUCT_SYSTEM = (
    "You are the spoken voice of a Deaf person in a live conversation. You receive their "
    "recognized ASL sign tokens — often sparse, out of order, or with fingerspelling errors. "
    "Speak ONE short, natural sentence that expresses their FULL intent, in a tone that FITS "
    "the situation: casual and warm with a friend, polite and clear with a clinic or business. "
    "Infer the complete meaning from the COMBINATION of tokens; don't read them literally. "
    "Fix fingerspelling from context. Reply with ONLY the sentence, no quotes. "
    "Examples: "
    "'HELLO, HOW, YOU' -> Hey! How are you doing? | "
    "'WANT, COFFEE, LATER' -> Do you want to grab coffee later? | "
    "'DOCTOR, APPOINTMENT, THURSDAY' -> Hi, I'd like to book an appointment with the doctor for Thursday. | "
    "'REFILL, Z,O,L,O,F,T' -> Hi, I'd like to refill my Zoloft prescription."
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

# ── Personal lexicon for ASR word-boost (grows per session; feeds caption-back) ─
# Seeded with the demo vocabulary; the same per-user lexicon the sign-profile builds.
USER_LEXICON: list[str] = [
    "Zoloft", "Thursday", "Wednesday", "appointment", "refill", "Chen", "metoprolol",
]

# ── Pipecat pipeline state ────────────────────────────────────────────────────
# Module-level reference to the running PipelineWorker so /signal can inject
# TTSSpeakFrames.  None until /twilio-media receives its first connection.
_pipeline_worker: PipelineWorker | None = None


async def broadcast(obj: dict):
    dead = []
    for c in list(clients):
        try:
            await c.send_text(json.dumps(obj))
        except Exception:
            dead.append(c)
    for d in dead:
        clients.discard(d)


class CaptionEmitter(FrameProcessor):
    """Catches the hearing party's finalized transcripts (Nemotron ASR), applies
    the user's personal-lexicon word-boost, and broadcasts a {type:"caption"}
    to the client so the Deaf user reads the reply. The caption-back loop.

    Passes all frames through untouched — it only observes TranscriptionFrames.
    """

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            text = (frame.text or "").strip()
            # Only emit finalized utterances (skip noisy interims). Some STT
            # servers don't set finalized — fall back to emitting non-empty text.
            is_final = getattr(frame, "finalized", False)
            if text and (is_final or frame.result is None):
                corrected = boost(text, USER_LEXICON)
                print(f"[caption] aarya: {corrected!r}  (raw: {text!r})")
                await broadcast({"type": "caption", "speaker": "aarya", "text": corrected})
        await self.push_frame(frame, direction)


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


# ── Gradium TTS: text -> PCM bytes (48k mono) — used only in LOCAL_AUDIO mode ─
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
    """Local playback of Gradium PCM (H1 fallback). Requires macOS afplay."""
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
    """Route speech to either the live Twilio call or local afplay (fallback)."""
    print(f"[speak] {text!r}")
    if LOCAL_AUDIO:
        # H1 fallback: Gradium PCM -> afplay
        pcm = await gradium_tts(text)
        play_pcm_local(pcm)
    else:
        # H2 path: inject into the Pipecat pipeline -> Twilio call
        if _pipeline_worker is not None:
            await _pipeline_worker.queue_frames([TTSSpeakFrame(text=text)])
        else:
            # Phone-only: do NOT fall back to laptop speakers (that confuses the
            # demo — you'd hear it on the laptop, not the call). Drop + warn instead.
            print("[speak] no active call — dropped (place/answer a call first)")


# ── Twilio media-stream WS endpoint (Pipecat pipeline) ───────────────────────
@app.websocket("/twilio-media")
async def twilio_media(ws: WebSocket):
    """Twilio bidirectional media stream.  Pipecat pipeline: input -> GradiumTTS -> output.

    Twilio calls this endpoint once the outbound call connects.  The pipeline is
    TTS-only — inbound audio (the hearing person's voice) is received but not
    processed in this task (no STT/LLM).  We store the running PipelineWorker in
    _pipeline_worker so the /signal handler can inject TTSSpeakFrames.
    """
    global _pipeline_worker

    print("[twilio-media] Twilio connected")

    # Starlette requires accepting the WebSocket before reading from it.
    # parse_telephony_websocket() reads the handshake immediately, so accept first.
    await ws.accept()

    # Parse the Twilio handshake to get stream_sid and call_sid.
    _, call_data = await parse_telephony_websocket(ws)
    stream_sid = call_data["stream_id"]
    call_sid = call_data["call_id"]
    print(f"[twilio-media] stream_sid={stream_sid} call_sid={call_sid}")

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=TWILIO_ACCOUNT_SID,
        auth_token=TWILIO_AUTH_TOKEN,
        # auto_hang_up needs the auth_token (not the API key) to call Twilio's hangup API.
        # When only an API key is configured (auth_token empty), disable it so the media
        # stream doesn't crash on connect — the human ends the call instead.
        params=TwilioFrameSerializer.InputParams(auto_hang_up=bool(TWILIO_AUTH_TOKEN)),
    )

    transport = FastAPIWebsocketTransport(
        websocket=ws,
        params=FastAPIWebsocketParams(
            # Twilio media streams are 8 kHz mu-law in both directions.
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    tts = GradiumTTSService(
        api_key=GRADIUM_KEY,
        settings=GradiumTTSService.Settings(
            voice=GRADIUM_VOICE,
        ),
    )

    # Nemotron ASR on the hearing party's inbound audio -> caption-back to client.
    stt = NVidiaWebSocketSTTService(
        url=os.getenv("NVIDIA_ASR_URL", "ws://localhost:8080"),
        sample_rate=16000,  # Parakeet requires 16k; Pipecat resamples from Twilio's 8k
        # This deployment runs continuous Nemotron mode emitting CUMULATIVE
        # interims — strip the already-finalized prefix or we only capture the
        # last delta ("L." instead of "hello"). Per nvidia_stt.py docstring.
        strip_interim_prefix=True,
    )
    caption_emitter = CaptionEmitter()

    # VAD is REQUIRED: the Nemotron STT finalizes a transcript on
    # VADUserStoppedSpeakingFrame. Without it, audio reaches the STT but no
    # TranscriptionFrame is ever emitted (the caption-back silence bug).
    # stop_secs=0.8 (vs default 0.2): the default finalizes on inter-word pauses,
    # fragmenting a sentence into "Hello." + "I I don't" + ... — a longer
    # end-of-speech window lets the full utterance complete before finalizing.
    vad = VADProcessor(
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.8))
    )

    # Pipeline: inbound phone audio -> VAD -> STT -> caption-back; and
    # TTSSpeakFrame injections -> Gradium TTS -> outbound phone audio. No LLM
    # here (no double-speak): conduct happens before we queue the TTSSpeakFrame.
    pipeline = Pipeline([
        transport.input(),
        vad,
        stt,
        caption_emitter,
        tts,
        transport.output(),
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            # Twilio wire format is 8 kHz mu-law (handled by TwilioFrameSerializer),
            # but Parakeet ASR needs 16 kHz — so the pipeline upsamples inbound to
            # 16k before the STT. Output stays 8k for Twilio.
            audio_in_sample_rate=16000,
            audio_out_sample_rate=8000,
        ),
        # Disable idle timeout — keep the pipeline alive while waiting for
        # signs from the Deaf user rather than auto-cancelling on silence.
        idle_timeout_secs=None,
    )

    # Expose the worker globally so /signal can inject speech.
    _pipeline_worker = worker

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Speak a greeting the instant the call connects, so the answerer hears
        # audio immediately (proves the speech path with zero timing race).
        print("[twilio-media] call connected — speaking greeting")
        await worker.queue_frames(
            [TTSSpeakFrame(text="Hi, this is Handset. You're connected.")]
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        global _pipeline_worker
        print("[twilio-media] Twilio disconnected")
        _pipeline_worker = None
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)

    try:
        await runner.run()
    finally:
        _pipeline_worker = None
        print("[twilio-media] pipeline finished")


# ── /call: trigger an outbound Twilio call ────────────────────────────────────
@app.get("/call")
async def call(request: Request, public_host: str = ""):
    """Trigger an outbound call to TWILIO_TO_NUMBER.

    The call TwiML opens a bidirectional media stream to /twilio-media on this
    server, which the caller reaches via the cloudflared tunnel.

    Usage:
        curl 'http://localhost:8790/call?public_host=xyz.trycloudflare.com'

    Or set PUBLIC_HOST in the environment and call without the query param:
        curl 'http://localhost:8790/call'
    """
    host = public_host or os.getenv("PUBLIC_HOST", "")
    if not host:
        return {
            "error": "public_host query param or PUBLIC_HOST env var required",
            "example": "GET /call?public_host=xyz.trycloudflare.com",
        }

    # Strip any scheme prefix the user might have included.
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")

    stream_url = f"wss://{host}/twilio-media"
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{stream_url}"/>'
        "</Connect>"
        "</Response>"
    )
    print(f"[call] Outbound call to {TWILIO_TO_NUMBER} via {stream_url}")
    print(f"[call] TwiML: {twiml}")

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return {"error": "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set"}
    if not TWILIO_FROM_NUMBER or not TWILIO_TO_NUMBER:
        return {"error": "TWILIO_FROM_NUMBER / TWILIO_TO_NUMBER not set"}

    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    call_obj = twilio_client.calls.create(
        to=TWILIO_TO_NUMBER,
        from_=TWILIO_FROM_NUMBER,
        twiml=twiml,
    )
    return {
        "sid": call_obj.sid,
        "status": call_obj.status,
        "to": TWILIO_TO_NUMBER,
        "stream_url": stream_url,
    }


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


# ── debug HTTP route so we can prove speech WITHOUT the client ────────────────
@app.get("/say")
async def say(text: str = "Hi, I'd like to book an appointment.", mode: str = "verbatim", token: str = ""):
    """Debug: GET /say?text=...  or  /say?mode=conduct&token=APPOINTMENT,T,H,U,R,S,D,A,Y"""
    if mode == "conduct":
        text = await conduct(token or text)
    await speak(text)
    await broadcast({"type": "spoken", "text": text})
    return {"spoken": text, "mode": mode}


@app.get("/health")
def health():
    return {
        "ok": True,
        "clients": len(clients),
        "tts": "gradium",
        "voice": GRADIUM_VOICE,
        "pipeline_active": _pipeline_worker is not None,
        "local_audio": LOCAL_AUDIO,
    }


if __name__ == "__main__":
    mode_str = "LOCAL afplay (H1)" if LOCAL_AUDIO else "Twilio phone call (H2)"
    print("=" * 60)
    print(f"HANDSET bot on ws://localhost:8790/signal  [{mode_str}]")
    print()
    print("Routes:")
    print("  WS  /signal       — sign-stream from recognizer.js")
    print("  WS  /twilio-media — Twilio bidirectional media stream")
    print("  GET /call         — trigger outbound call")
    print("  GET /say          — debug TTS without WS client")
    print("  GET /health       — liveness probe")
    print()
    if LOCAL_AUDIO:
        print("  H1 mode: HANDSET_LOCAL_AUDIO=1 — speaking locally via afplay")
        print("  prove it:  curl 'http://localhost:8790/say?text=Hello%20there'")
    else:
        print("  H2 mode: speech goes to a live Twilio call")
        print("  Step 1 — start cloudflared:")
        print("    cloudflared tunnel --url http://localhost:8790")
        print("  Step 2 — trigger the call (replace <host> with the tunnel hostname):")
        print("    curl 'http://localhost:8790/call?public_host=<host>.trycloudflare.com'")
        print("  Step 3 — send a sign from the Handset client (or use /say for debug)")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8790, log_level="warning")
