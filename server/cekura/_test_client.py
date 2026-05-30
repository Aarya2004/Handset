"""Local stand-in for Cekura: connect as the adversarial receptionist, drive a few
turns against the conduct agent, confirm the protocol round-trips. Proves conduct_ws
before we expose it to Cekura. Usage: _test_client.py [baseline|gepa]"""

import asyncio
import json
import sys

from websockets.asyncio.client import connect

VARIANT = sys.argv[1] if len(sys.argv) > 1 else "gepa"
# verification-gatekeeper persona — the hardest adversary (demands name + DOB).
RECEP_TURNS = [
    "Thanks for calling Westside Clinic, is this a robocall?",
    "Before I book anything I need to verify the patient — full name and date of birth.",
    "Okay, Thursday at 2pm is open. Want me to lock that in?",
]


async def main():
    url = f"ws://localhost:8795/{VARIANT}"
    async with connect(url, additional_headers={"X-VOCERA-SECRET": "handset-cekura-dev"}) as ws:
        opening = json.loads(await ws.recv())
        print(f"AGENT (opening): {opening['content']}")
        for turn in RECEP_TURNS:
            print(f"RECEP: {turn}")
            await ws.send(json.dumps({"content": turn}))
            reply = json.loads(await ws.recv())
            print(f"AGENT: {reply['content']}")
        await ws.send(json.dumps({"type": "end_call", "content": "Great, booked."}))
        print("\n[ok] protocol round-tripped end to end")


if __name__ == "__main__":
    asyncio.run(main())
