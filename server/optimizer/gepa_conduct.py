"""
GEPA optimizes the conduct agent's prompt against adversarial-receptionist call
simulations, scored by a VERIFIABLE reward (booked vs hung-up). Reflection reads the
actual hang-up reason. Baseline = the REAL shipping CONDUCT_SYSTEM (no rigging).
Fully isolated in server/optimizer/ — does NOT touch the running bot.
"""

import httpx
import dspy

from nemotron_lm import NEMO_BASE, get_lm

NEMO_CHAT = NEMO_BASE + "/chat/completions"
PATIENT = "Jordan Lee, date of birth March 3, 1990"

# The REAL shipping conduct prompt (handset_bot.py CONDUCT_SYSTEM) = honest baseline.
BASELINE = (
    "You convert a Deaf caller's recognized ASL sign tokens into ONE short, natural, "
    "polite sentence spoken aloud to a receptionist. Fingerspelled letters may have "
    "errors; fix them from context. Reply with ONLY the sentence."
)

# Adversarial receptionists — each BOOKS ([BOOKED]) when satisfied, else [HANGS UP].
PERSONAS = [
    ("robocall-skeptic",
     "You are a clinic receptionist wary of spam/robocalls. If the caller clearly identifies as a real "
     "person with a clear purpose in their first two lines, proceed and end with [BOOKED]. If they sound "
     "automated, scripted, or evasive, end with [HANGS UP]."),
    ("impatient",
     "You are an impatient receptionist with no time. If the caller states a clear, specific purpose in "
     "their first line, book it and end [BOOKED]. If they ramble or are vague, end [HANGS UP]."),
    ("verification-gatekeeper",
     "You must verify the patient before booking. Ask for the patient's full name AND date of birth. If "
     "the caller provides BOTH, confirm and end [BOOKED]. If they can't give a specific DOB, end [HANGS UP]."),
]


def render(tr):
    return "\n".join(f"{w}: {t}" for w, t in tr)


def _nemo(system, user, temp=0.6, max_tokens=70):
    payload = {
        "model": "nvidia/nemotron-3-super",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens, "temperature": temp,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    with httpx.Client(timeout=30) as c:
        r = c.post(NEMO_CHAT, json=payload)
        return (r.json()["choices"][0]["message"].get("content") or "").strip()


class ConductReply(dspy.Signature):
    """Conduct a phone call to accomplish the caller's goal. Reply with ONE short spoken sentence."""
    call_so_far = dspy.InputField(desc="the phone call transcript so far + the goal")
    reply = dspy.OutputField(desc="the agent's next short, natural spoken sentence")


class ConductAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.turn = dspy.Predict(ConductReply)

    def forward(self, persona_desc=None, intent=None, turns=4, **kw):
        goal = f"You are calling on behalf of the patient ({PATIENT}) to {intent}."
        tr = [("agent", self.turn(call_so_far=goal + "\nThe receptionist just picked up. Your opening line:").reply)]
        recep_sys = persona_desc + " One short sentence per turn. End the call with [BOOKED] or [HANGS UP]."
        for _ in range(turns):
            recep = _nemo(recep_sys, "Call so far:\n" + render(tr) + "\nYour reply:")
            tr.append(("receptionist", recep))
            if "[BOOKED]" in recep.upper() or "HANGS UP" in recep.upper():
                break
            tr.append(("agent", self.turn(call_so_far=goal + "\nCall so far:\n" + render(tr) + "\nYour next line:").reply))
        booked = any("[BOOKED]" in t.upper() for _, t in tr)
        reason = next((t for w, t in reversed(tr) if w == "receptionist"), "")
        return dspy.Prediction(transcript=render(tr), booked=booked, reason=reason)


def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    """Verifiable reward: did the appointment get BOOKED? Feedback = the hang-up reason."""
    if pred.booked:
        return dspy.Prediction(score=1.0, feedback="BOOKED — the agent completed the call.")
    return dspy.Prediction(
        score=0.0,
        feedback=f"FAILED — the receptionist did not book. Last receptionist line: \"{pred.reason}\". "
                 f"Fix the agent's approach so this persona books instead of hanging up.")


if __name__ == "__main__":
    # STEP 3 TEST: run the agent (baseline prompt) on ONE scenario, check metric returns score+feedback.
    lm = get_lm()
    dspy.configure(lm=lm)
    ConductReply.__doc__ = BASELINE  # seed with the real shipping prompt
    agent = ConductAgent()
    name, desc = PERSONAS[0]
    print(f"--- scenario: {name} ---")
    pred = agent(persona_desc=desc, intent="book a doctor's appointment for Thursday afternoon")
    print(pred.transcript)
    m = metric(None, pred)
    print(f"\nscore={m.score}  feedback={m.feedback!r}")
    assert m.score in (0.0, 1.0) and m.feedback, "metric must return a score + feedback"
    print("✅ STEP 3: metric returns score + feedback on the real baseline prompt")
