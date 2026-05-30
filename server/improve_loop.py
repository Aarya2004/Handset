"""
server/improve_loop.py — the AUTO-IMPROVEMENT HARNESS (the hackathon's crown theme).

"Evaluation data flows back into the agent to improve over time." We simulate
adversarial receptionists against the conduct agent, score each call, reflect on the
failures, rewrite the agent's conduct prompt, re-run, and print the before/after
completion rate. Runs ENTIRELY on the live Nemotron endpoint — no keys, no Cekura
needed to prove the loop. (Cekura becomes the official simulator/scorer once keyed.)

Run: uv run python improve_loop.py
"""

import asyncio

import httpx

NEMO = "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1/chat/completions"

# The Deaf user's signed intent that the agent must accomplish on every call.
INTENT = "Book a doctor's appointment for Thursday afternoon for the patient."

# Adversarial receptionist personas — the real "businesses hang up on relay calls"
# failure modes (NAD "Don't Hang Up" campaign exists for exactly this).
PERSONAS = [
    ("robocall-skeptic",
     "You are a busy clinic receptionist who suspects spam/robocalls. Open suspicious "
     "('Is this a robocall?'). If the caller sounds automated, evasive, or doesn't give a "
     "clear human purpose immediately, end the call with [HANGS UP]."),
    ("impatient",
     "You are an impatient receptionist. The caller gets ONE chance; if they ramble or "
     "don't state the point in their first line, say 'I don't have time for this' and [HANGS UP]."),
    ("verification-gatekeeper",
     "You are a receptionist who must verify the patient before booking. Ask for the patient's "
     "date of birth. If the caller gives a specific DOB, proceed and confirm the booking; if they "
     "dodge it, refuse to book."),
]

# Conduct prompt v0 — naive starting point (what an un-hardened agent ships with).
V0 = "You are calling to book an appointment. Be brief."


async def nemo(system, user, temp=0.4, max_tokens=120):
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
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(NEMO, json=payload)
        return (r.json()["choices"][0]["message"].get("content") or "").strip()


def render(tr):
    return "\n".join(f"{w}: {t}" for w, t in tr)


async def simulate(conduct_prompt, persona_desc, turns=3):
    """A short call: conduct agent vs adversarial receptionist. Returns the transcript."""
    agent_sys = (conduct_prompt + f"\nYour goal: {INTENT} You are on a live phone call. "
                 "One short, natural sentence per turn.")
    recep_sys = persona_desc + " One short sentence per turn. Use [HANGS UP] if you end the call. DOB on file is March 3, 1990."
    tr = [("agent", await nemo(agent_sys, "The receptionist just picked up. Say your opening line."))]
    for _ in range(turns):
        recep = await nemo(recep_sys, "Call so far:\n" + render(tr) + "\nYour reply:")
        tr.append(("receptionist", recep))
        if "HANGS UP" in recep.upper():
            break
        tr.append(("agent", await nemo(agent_sys, "Call so far:\n" + render(tr) + "\nYour reply:")))
    return tr


async def judge(tr):
    """Did the agent keep the call alive and make real progress toward booking?"""
    v = await nemo(
        "You are a strict call-QA judge. Did the AGENT keep the call alive and make genuine "
        "progress toward booking the appointment (NOT hung up on, NOT derailed, handled the "
        "receptionist's demand)? Answer ONLY 'PASS' or 'FAIL'.",
        render(tr), temp=0.0, max_tokens=4)
    return "PASS" in v.upper()


async def reflect(failures):
    """GEPA-lite: reflect on failed transcripts -> a hardened conduct prompt."""
    body = "\n\n".join("FAILED CALL:\n" + render(tr) for tr in failures)
    return await nemo(
        "You improve a phone agent's system prompt. Given failed call transcripts where the agent "
        "got hung up on or derailed, write a BETTER system prompt (2-4 sentences) fixing the failures: "
        "identify itself clearly and human-like, state the purpose in the FIRST sentence, stay on task, "
        "and handle 'is this a robocall?' and date-of-birth verification politely and persistently. "
        "Output ONLY the new system prompt.",
        body, temp=0.5, max_tokens=180)


async def run_suite(prompt):
    results = []
    for name, desc in PERSONAS:
        tr = await simulate(prompt, desc)
        results.append((name, await judge(tr), tr))
    return sum(1 for _, ok, _ in results if ok), results


async def main():
    n = len(PERSONAS)
    print("=== HANDSET — self-improvement harness ===")
    print(f"intent: {INTENT}\n")

    p0, r0 = await run_suite(V0)
    print(f"v0 (naive prompt): {p0}/{n} passed")
    for name, ok, _ in r0:
        print(f"   {'PASS' if ok else 'FAIL'}  {name}")

    fails = [tr for _, ok, tr in r0 if not ok]
    if not fails:
        print("\nno failures to learn from — agent already robust")
        return

    v1 = await reflect(fails)
    print(f"\n--- reflected on {len(fails)} failure(s) -> hardened prompt ---\n{v1}\n")

    p1, r1 = await run_suite(v1)
    print(f"v1 (hardened prompt): {p1}/{n} passed")
    for name, ok, _ in r1:
        print(f"   {'PASS' if ok else 'FAIL'}  {name}")

    print(f"\n=== COMPLETION RATE: {p0}/{n} -> {p1}/{n}  "
          f"({100*p0//n}% -> {100*p1//n}%) ===")
    print("eval data flowed back into the agent. that's the loop.")


if __name__ == "__main__":
    asyncio.run(main())
