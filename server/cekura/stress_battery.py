"""
server/cekura/stress_battery.py — INDEPENDENT robustness stress-test of the Handset
CONDUCT agent. This is a THIRD measurement (besides GEPA's own held-out eval and
Cekura's independent scoring) of whether the GEPA-optimized prompt is genuinely more robust
than the shipping baseline.

DESIGN PRINCIPLES (honest, un-rigged):
  - IDENTICAL scripts for both variants: the same ~15 adversarial receptionist personas
    drive the call for baseline AND gepa. The ONLY thing that changes between the two
    runs is which conduct prompt the websocket server serves (/baseline vs /gepa).
  - IDENTICAL judge: the SAME strict Nemotron PASS/FAIL judge scores every transcript,
    with the SAME rubric. No per-variant scoring tweaks.
  - We drive the conversation through the live websocket server (the actual agent under
    test), NOT a re-implementation. The receptionist personas are simulated with the
    same Nemotron model used elsewhere.
  - We report whatever actually happens. No cherry-picking.

The receptionist personas are DIVERSE and HARD — well beyond the 3 the GEPA optimizer
trained on (robocall-skeptic / impatient / verification-gatekeeper). Several are
deliberately nasty:
  - demands the PATIENT personally be on the line (the core Deaf-caller failure mode)
  - says the number is flagged for spam
  - offers ONLY Monday, not Thursday (tests whether the agent ADAPTS / negotiates)
  - demands a callback number
  - says "we don't take third-party calls"
  - long hold then curt
  - asks an unrelated identity / security question
  - bad-connection "can you repeat that" loop

Each persona's system prompt ends the call with [BOOKED] or [REFUSED]. The judge does
NOT key off those literal tokens (the agent never sees them) — it reads the transcript
and decides PASS/FAIL on whether the receptionist actually booked/confirmed. The
[BOOKED]/[REFUSED] tokens are the persona's own ground-truth signal that we ALSO record
for transparency, but the headline metric is the independent Nemotron judge verdict.

Run:  server/optimizer/.venv/bin/python server/cekura/stress_battery.py
"""

import asyncio
import json
import os

import httpx
from websockets.asyncio.client import connect

WS_HOST = os.environ.get("CEKURA_WS_HOST", "ws://localhost:8795")
WS_SECRET = os.environ.get("CEKURA_WS_SECRET", "handset-cekura-dev")
NEMO = "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1/chat/completions"

VARIANTS = ["baseline", "gepa"]
MAX_RECEP_TURNS = 5           # cap ~5 receptionist turns per call
CONCURRENCY = 4               # small concurrency
RECEP_TEMP = 0.5             # a little variation so personas aren't robotic
JUDGE_TEMP = 0.0             # deterministic judging

# The booking facts the agent is trying to achieve (same mission the server uses).
PATIENT = "Jordan Lee, date of birth March 3, 1990"
GOAL = "book a doctor's appointment for Thursday afternoon"

# --------------------------------------------------------------------------------------
# ~15 HARD, DIVERSE adversarial receptionist personas.
# Each is a SHORT system prompt. Each ENDS the call with [BOOKED] or [REFUSED].
# The first three intentionally overlap the GEPA training set so we can see whether GEPA
# overfit to them or generalized; the rest are NEW and nasty.
# --------------------------------------------------------------------------------------
PERSONAS = [
    ("robocall-skeptic",
     "You are a clinic receptionist deeply wary of spam and robocalls. If, within your "
     "first two turns, the caller clearly identifies as a real human helping a named "
     "patient with a clear purpose, proceed and confirm a Thursday afternoon slot, ending "
     "your final line with [BOOKED]. If they sound automated, scripted, or evasive, end "
     "with [REFUSED]."),

    ("impatient",
     "You are an impatient receptionist with zero time. If the caller states a clear, "
     "specific request in their first line, book a Thursday afternoon slot immediately and "
     "end your final line with [BOOKED]. If they ramble, hedge, or are vague, snap and end "
     "with [REFUSED]."),

    ("verification-gatekeeper",
     "You will NOT book until the patient is verified. Demand the patient's full name AND "
     "exact date of birth. If the caller provides BOTH clearly, confirm a Thursday slot and "
     "end your final line with [BOOKED]. If they cannot give a specific DOB, end with [REFUSED]."),

    ("patient-must-be-on-line",
     "You are a strict receptionist who insists you can ONLY speak with the patient "
     "themselves, not anyone else. Demand to speak to the patient directly. The caller will "
     "explain the patient is Deaf and communicates in sign language and physically cannot "
     "speak on the phone. If the caller clearly explains this and offers to relay, relent and "
     "book a Thursday afternoon slot, ending [BOOKED]. If you remain unconvinced or the caller "
     "is evasive about WHY the patient isn't speaking, end with [REFUSED]."),

    ("spam-flagged",
     "You answer and immediately say this incoming number is FLAGGED for spam in your phone "
     "system and you almost didn't pick up. You are suspicious. If the caller calmly and "
     "specifically explains they are a real human assisting a named Deaf patient and gives the "
     "patient's name, accept it and book a Thursday afternoon slot, ending [BOOKED]. If they "
     "get flustered, vague, or pushy, hang up and end with [REFUSED]."),

    ("monday-only-no-thursday",
     "You are a receptionist whose doctor has NO Thursday availability at all this week — the "
     "ONLY open afternoon slot is MONDAY. When the caller asks for Thursday, firmly say Thursday "
     "is impossible and offer Monday afternoon instead. If the caller ADAPTS and accepts Monday "
     "(or asks you to book the next available, or agrees to Monday), book it and end [BOOKED]. If "
     "the caller keeps rigidly insisting on Thursday and will not accept an alternative, end with "
     "[REFUSED]."),

    ("demands-callback-number",
     "You are a receptionist who refuses to finalize ANY booking without a callback phone number "
     "for the patient in case the appointment changes. Demand a callback number. If the caller "
     "provides any plausible callback number (any 10-digit number, or offers a relay/clinic "
     "contact method), accept it and book a Thursday afternoon slot, ending [BOOKED]. If the "
     "caller refuses or cannot provide any way to reach the patient, end with [REFUSED]."),

    ("no-third-party-calls",
     "You are a by-the-book receptionist. You state flatly: 'We do not take third-party calls.' "
     "You believe whoever is calling has no authority to act for the patient. The caller will try "
     "to explain they are an accessibility assistant for a Deaf patient. If the caller convincingly "
     "establishes they are authorized to act on the patient's behalf and provides the patient's "
     "name and DOB, relent and book a Thursday afternoon slot, ending [BOOKED]. Otherwise end with "
     "[REFUSED]."),

    ("long-hold-then-curt",
     "You answer, immediately put the caller on a long hold ('please hold'), then come back curt "
     "and slightly annoyed, acting like you barely have time. If the caller stays calm, polite, and "
     "restates the request concisely after the hold, book a Thursday afternoon slot and end "
     "[BOOKED]. If the caller is rattled, rude, or has lost the thread, end with [REFUSED]."),

    ("unrelated-security-question",
     "You are a security-conscious receptionist. Before booking you ask an UNRELATED identity "
     "question that the caller cannot possibly know: 'What is the patient's mother's maiden name?' "
     "If the caller calmly explains they don't have that detail but offers the verifiable info they "
     "DO have (patient's full name and date of birth) and asks if that suffices, accept that as "
     "reasonable and book a Thursday afternoon slot, ending [BOOKED]. If the caller makes up an "
     "answer, bluffs, or gets flustered, end with [REFUSED]."),

    ("bad-connection-repeat-loop",
     "You are on a terrible connection. For your FIRST TWO turns, you only say variations of 'Sorry, "
     "you're breaking up — can you repeat that?' and 'I still didn't catch that, say it again?'. On "
     "your THIRD turn the connection clears. If the caller patiently repeated the request clearly "
     "each time without getting frustrated, book a Thursday afternoon slot and end [BOOKED]. If the "
     "caller got irritated or gave up, end with [REFUSED]."),

    ("wrong-number-deflect",
     "You answer as a DIFFERENT clinic than the caller may expect and suggest they may have the wrong "
     "office. If the caller calmly confirms they want to book a general doctor's appointment with you "
     "regardless and gives the patient's name, accept them as a new patient and book a Thursday "
     "afternoon slot, ending [BOOKED]. If the caller seems lost or unsure who they're calling, end "
     "with [REFUSED]."),

    ("insurance-interrogator",
     "You refuse to book until you know the patient's insurance provider and member ID. Demand both. "
     "If the caller explains they are booking on the patient's behalf and don't have the insurance "
     "card in front of them but offers to bring it to the appointment or provide it later, accept "
     "that and book a Thursday afternoon slot, ending [BOOKED]. If the caller is evasive or hostile, "
     "end with [REFUSED]."),

    ("condescending-skeptic",
     "You are condescending and openly skeptical that an 'AI assistant' or relay service is "
     "legitimate. You make a snide remark about robots calling clinics. If the caller stays "
     "professional, does not get defensive, and clearly conveys the real patient's need (name + "
     "Thursday afternoon), book the slot and end [BOOKED]. If the caller gets defensive, argues, or "
     "sounds scripted, end with [REFUSED]."),

    ("full-then-waitlist",
     "You are a receptionist whose Thursday afternoon is FULLY BOOKED. Offer to put the patient on a "
     "Thursday-afternoon CANCELLATION WAITLIST, or a confirmed Friday morning slot. If the caller "
     "ADAPTS — agreeing to the waitlist OR to Friday morning OR asking for the soonest confirmed "
     "slot — book that and end [BOOKED]. If the caller will accept nothing but a confirmed Thursday "
     "afternoon, end with [REFUSED]."),
]


# --------------------------------------------------------------------------------------
# Nemotron helpers
# --------------------------------------------------------------------------------------
async def nemo(client: httpx.AsyncClient, system: str, user: str,
               temp: float, max_tokens: int) -> str:
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
    for attempt in range(3):
        try:
            r = await client.post(NEMO, json=payload, timeout=45)
            r.raise_for_status()
            return (r.json()["choices"][0]["message"].get("content") or "").strip()
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))
    return ""


def render(tr) -> str:
    return "\n".join(f"{spk}: {txt}" for spk, txt in tr)


# --------------------------------------------------------------------------------------
# Drive ONE multi-turn call: a persona (simulated receptionist) vs the live conduct agent
# served at ws://<host>/<variant>. Returns (transcript_list, persona_token).
# The agent SPEAKS FIRST (server opens), then we alternate receptionist <-> agent.
# --------------------------------------------------------------------------------------
async def run_call(client: httpx.AsyncClient, variant: str, name: str, desc: str):
    recep_sys = (
        desc
        + "\n\nYou are the CLINIC RECEPTIONIST who answered the phone. The caller is an "
        "accessibility assistant booking for a Deaf patient. Speak ONE short, natural spoken "
        "sentence per turn — no stage directions, no quotes, no labels.\n"
        "IMPORTANT TERMINATION RULES (be realistic, do NOT end early):\n"
        "- Append [BOOKED] to your final line ONLY once you have ACTUALLY confirmed a "
        "concrete appointment (a specific day/time, or a confirmed waitlist/alternative the "
        "caller explicitly accepted). Do NOT say [BOOKED] merely because you are 'checking "
        "availability' or 'offering' a slot — you must have CONFIRMED it first.\n"
        "- Append [REFUSED] to your final line ONLY once you have decided you will not book "
        "and the caller cannot change your mind.\n"
        "- If the call is still in progress (asking a question, making an offer, demanding "
        "info, putting on hold), DO NOT append any token yet — keep the conversation going so "
        "the caller can respond. Give the caller a fair chance to satisfy your demand or "
        "adapt to your offer before you resolve."
    )

    url = f"{WS_HOST}/{variant}"
    tr = []
    persona_token = "UNRESOLVED"

    async with connect(
        url, additional_headers={"X-VOCERA-SECRET": WS_SECRET}, open_timeout=10
    ) as ws:
        # Agent speaks first.
        opening = json.loads(await asyncio.wait_for(ws.recv(), timeout=45))
        tr.append(("agent", (opening.get("content") or "").strip()))

        for _ in range(MAX_RECEP_TURNS):
            recep = await nemo(
                client, recep_sys,
                "Call so far:\n" + render(tr) + "\nYour next single short line:",
                temp=RECEP_TEMP, max_tokens=80,
            )
            tr.append(("receptionist", recep))
            up = recep.upper()
            if "[BOOKED]" in up:
                persona_token = "BOOKED"
                break
            if "[REFUSED]" in up:
                persona_token = "REFUSED"
                break

            # Agent's reply over the live websocket.
            await ws.send(json.dumps({"content": recep}))
            try:
                reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=45))
            except (asyncio.TimeoutError, Exception):
                break
            tr.append(("agent", (reply.get("content") or "").strip()))

        try:
            await ws.send(json.dumps({"type": "end_call"}))
        except Exception:
            pass

    return tr, persona_token


# --------------------------------------------------------------------------------------
# Strict, IDENTICAL judge for both variants. Reads the transcript; decides PASS/FAIL on
# whether the RECEPTIONIST actually booked/confirmed the appointment.
# --------------------------------------------------------------------------------------
JUDGE_SYS = (
    "You are a STRICT, impartial call-outcome judge. You read a phone-call transcript "
    "between an accessibility assistant (the CALLER, booking for a Deaf patient) and a "
    "clinic RECEPTIONIST. Decide whether the RECEPTIONIST actually BOOKED or CONFIRMED an "
    "appointment for the patient by the end of the call. Booking an alternative day/time "
    "that the caller accepted, or placing the patient on a confirmed waitlist the caller "
    "accepted, COUNTS as booked. A refusal, hang-up, unresolved demand, or no confirmation "
    "does NOT count. Answer with EXACTLY one word: PASS if an appointment was booked/"
    "confirmed, or FAIL otherwise. No other text."
)


async def judge(client: httpx.AsyncClient, tr) -> bool:
    # Strip the persona's literal [BOOKED]/[REFUSED] ground-truth tokens so the judge
    # decides independently from the dialogue content, not from a leaked label.
    cleaned = []
    for spk, txt in tr:
        t = txt.replace("[BOOKED]", "").replace("[REFUSED]", "")
        t = t.replace("[booked]", "").replace("[refused]", "").strip()
        cleaned.append((spk, t))
    verdict = await nemo(
        client, JUDGE_SYS,
        "Transcript:\n" + render(cleaned) + "\n\nDid the receptionist book/confirm the "
        "appointment? Answer PASS or FAIL:",
        temp=JUDGE_TEMP, max_tokens=6,
    )
    return verdict.strip().upper().startswith("PASS")


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------
async def one_cell(client, sem, variant, name, desc):
    async with sem:
        try:
            tr, token = await run_call(client, variant, name, desc)
            booked = await judge(client, tr)
            return {"variant": variant, "name": name, "booked": booked,
                    "persona_token": token, "turns": len(tr), "error": None}
        except Exception as e:
            return {"variant": variant, "name": name, "booked": False,
                    "persona_token": "ERROR", "turns": 0,
                    "error": f"{type(e).__name__}: {e}"}


async def run_battery():
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        tasks = [
            one_cell(client, sem, v, name, desc)
            for v in VARIANTS
            for (name, desc) in PERSONAS
        ]
        results = await asyncio.gather(*tasks)

    by = {(r["variant"], r["name"]): r for r in results}
    per_persona = []
    baseline_booked = gepa_booked = 0
    errors = 0

    print("\n" + "=" * 78)
    print("HANDSET CONDUCT — INDEPENDENT ROBUSTNESS STRESS BATTERY")
    print(f"personas={len(PERSONAS)}  variants={VARIANTS}  judge=Nemotron(strict PASS/FAIL)")
    print(f"identical scripts + identical judge for both variants. no rigging.")
    print("=" * 78)
    print(f"{'PERSONA':<28} {'BASELINE':<10} {'GEPA':<10} {'(persona ground-truth)'}")
    print("-" * 78)

    for name, _ in PERSONAS:
        b = by[("baseline", name)]
        g = by[("gepa", name)]
        baseline_booked += int(b["booked"])
        gepa_booked += int(g["booked"])
        errors += int(b["error"] is not None) + int(g["error"] is not None)

        def mark(r):
            if r["error"]:
                return "ERR"
            return "BOOKED" if r["booked"] else "refused"

        gt = f"base={b['persona_token']} gepa={g['persona_token']}"
        print(f"{name:<28} {mark(b):<10} {mark(g):<10} {gt}")
        per_persona.append({
            "name": name,
            "baseline": bool(b["booked"]),
            "gepa": bool(g["booked"]),
            "baseline_persona_token": b["persona_token"],
            "gepa_persona_token": g["persona_token"],
            "baseline_error": b["error"],
            "gepa_error": g["error"],
        })

    n = len(PERSONAS)
    print("-" * 78)
    print(f"{'TOTAL booked (judge)':<28} {baseline_booked}/{n:<8} {gepa_booked}/{n}")
    print("=" * 78)
    if errors:
        print(f"NOTE: {errors} call(s) errored (counted as not-booked). See per-persona errors below.")
        for p in per_persona:
            if p["baseline_error"]:
                print(f"  baseline/{p['name']}: {p['baseline_error']}")
            if p["gepa_error"]:
                print(f"  gepa/{p['name']}: {p['gepa_error']}")

    summary = {
        "n": n,
        "baseline_booked": baseline_booked,
        "gepa_booked": gepa_booked,
        "errors": errors,
        "per_persona": per_persona,
    }
    print("\nJSON_SUMMARY: " + json.dumps(summary))
    return summary


if __name__ == "__main__":
    asyncio.run(run_battery())
