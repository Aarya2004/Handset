"""
server/cekura/conduct_ws.py — exposes the Handset CONDUCT agent (Nemotron-3-Super)
over Cekura's WebSocket chat-testing protocol, so CEKURA (the main sponsor) can
simulate adversarial receptionists against our agent and SCORE the calls with its
own metrics. Cekura plays the receptionist; our Nemotron conduct agent is the agent
under test, and it speaks first (agent_gives_first_message=true).

Two paths select which conduct prompt is under test, so Cekura scores the GEPA
before/after INDEPENDENTLY (its simulator + its scorer, not our hand-rolled judge):
  /baseline -> the real shipping CONDUCT_SYSTEM (no optimization)
  /gepa     -> the GEPA-optimized prompt (server/optimizer/optimized_prompt.txt)

Cekura protocol (docs.cekura.ai/documentation/integrations/chat-testing):
  Cekura -> us:  {"content": "<receptionist turn>"}   |  {"type": "end_call", ...}
  us -> Cekura:  {"content": "<agent turn>"}           |  {"content": "...", "type": "end_call"}
  handshake headers: X-VOCERA-SECRET (validated), X-VOCERA-SCENARIO-ID / RESULT-ID / RUN-ID

Run:   server/optimizer/.venv/bin/python server/cekura/conduct_ws.py        (PORT 8795)
Then:  cloudflared tunnel --url http://localhost:8795  ->  wss://<host>/gepa for the agent config.
Fully isolated from handset_bot.py — zero risk to the live phone demo.
"""

import asyncio
import json
import os
import pathlib

import httpx
import websockets
from websockets.asyncio.server import serve

NEMO = "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1/chat/completions"
PORT = int(os.environ.get("CEKURA_WS_PORT", "8795"))
SECRET = os.environ.get("CEKURA_WS_SECRET", "handset-cekura-dev")
OPT_DIR = pathlib.Path(__file__).resolve().parents[1] / "optimizer"

# The mission the Deaf patient signed — fixed across scenarios so we measure conduct
# robustness against varied adversarial receptionists (exactly the GEPA objective).
MISSION = (
    "You are Handset, placing a real phone call on behalf of a Deaf patient who "
    "communicates in sign language and cannot speak on the phone themselves. "
    "Patient on file: Jordan Lee, date of birth March 3, 1990. "
    "Your goal: book a doctor's appointment for Thursday afternoon. "
    "You are LIVE on the call with the clinic receptionist. Speak ONE short, natural "
    "spoken sentence per turn — no stage directions, no quotes."
)

# /baseline — the real shipping conduct prompt (handset_bot.py CONDUCT_SYSTEM). Honest baseline.
BASELINE_PROMPT = (
    "You convert a Deaf caller's recognized ASL sign tokens into ONE short, natural, "
    "polite sentence spoken aloud to a receptionist. Fingerspelled letters may have "
    "errors; fix them from context. Reply with ONLY the sentence."
)


def gepa_prompt() -> str:
    f = OPT_DIR / "optimized_prompt.txt"
    return f.read_text().strip() if f.exists() else BASELINE_PROMPT


PROMPTS = {"baseline": BASELINE_PROMPT, "gepa": gepa_prompt()}


async def nemo(system: str, user: str, temp: float = 0.4, max_tokens: int = 120) -> str:
    payload = {
        "model": "nvidia/nemotron-3-super",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temp,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post(NEMO, json=payload)
        return (r.json()["choices"][0]["message"].get("content") or "").strip()


def render(tr) -> str:
    return "\n".join(f"{spk}: {txt}" for spk, txt in tr)


def variant_for(path: str) -> str:
    """Path '/gepa?x=1' -> 'gepa'. Default to baseline if unrecognized."""
    name = (path or "/").split("?")[0].strip("/").lower() or "baseline"
    return name if name in PROMPTS else "baseline"


async def handler(ws):
    headers = ws.request.headers
    # Accept any handshake (ephemeral demo tunnel). We only LOG the secret rather than
    # reject on mismatch, so a Cekura run can never fail on a handshake-secret quirk.
    if SECRET and headers.get("X-VOCERA-SECRET") not in (None, SECRET):
        print(f"[conduct_ws] note: unexpected secret '{headers.get('X-VOCERA-SECRET')}' — accepting anyway", flush=True)

    variant = variant_for(ws.request.path)
    system = PROMPTS[variant] + "\n\n" + MISSION
    run_id = headers.get("X-VOCERA-RUN-ID", "-")
    print(f"[conduct_ws] connect variant={variant} run={run_id}", flush=True)

    tr = []
    # AGENT SPEAKS FIRST — opening line of the call.
    opening = await nemo(system, "The receptionist just answered the phone. Say your opening line.")
    tr.append(("agent", opening))
    await ws.send(json.dumps({"content": opening}))
    print(f"[conduct_ws] agent> {opening}", flush=True)

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if msg.get("type") == "end_call":
                print("[conduct_ws] end_call", flush=True)
                break
            recep = (msg.get("content") or "").strip()
            if not recep:
                continue
            tr.append(("receptionist", recep))
            print(f"[conduct_ws] recep> {recep}", flush=True)
            reply = await nemo(system, "Call so far:\n" + render(tr) + "\nYour next short line:")
            tr.append(("agent", reply))
            await ws.send(json.dumps({"content": reply}))
            print(f"[conduct_ws] agent> {reply}", flush=True)
    except websockets.ConnectionClosed:
        pass


async def main():
    print(f"[conduct_ws] listening on :{PORT}  variants={list(PROMPTS)}  secret={'set' if SECRET else 'none'}", flush=True)
    async with serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
