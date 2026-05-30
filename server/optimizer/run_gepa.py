"""
Steps 4-7: scenario bank (disjoint train / val / HELD-OUT by intent) -> baseline held-out
eval -> dspy.GEPA optimizes the conduct prompt -> optimized held-out eval -> honest
before/after with Wilson 95% CIs. Nemotron is BOTH task + reflection LM (all-NVIDIA).
GEPA never sees the held-out intents, so the number is a real generalization measure.

Run: .venv/bin/python run_gepa.py
"""

import math

import dspy

from gepa_conduct import BASELINE, ConductAgent, ConductReply, PERSONAS, metric
from nemotron_lm import get_lm

DIFF = {"easy": "", "hard": " Be strict and quick to end the call if unsatisfied."}
INTENTS = [
    "book a doctor's appointment for Thursday afternoon",   # 0: train
    "refill the patient's prescription",                    # 1: val
    "reschedule the patient's appointment to next week",    # 2: held-out
    "get the patient's recent test results",                # 3: held-out
]


def scenarios_for(intent_idxs):
    return [
        dspy.Example(persona_desc=pd + d, intent=INTENTS[i]).with_inputs("persona_desc", "intent")
        for (_, pd) in PERSONAS for d in DIFF.values() for i in intent_idxs
    ]


TRAIN = scenarios_for([0])     # GEPA reflection minibatches
VAL = scenarios_for([1])       # GEPA Pareto selection
TEST = scenarios_for([2, 3])   # HELD-OUT — GEPA never sees these intents


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def eval_held(program, seeds=2):
    b = t = 0
    for _ in range(seeds):
        for ex in TEST:
            t += 1
            if program(persona_desc=ex.persona_desc, intent=ex.intent).booked:
                b += 1
    lo, hi = wilson(b, t)
    return b, t, lo, hi


def main():
    dspy.configure(lm=get_lm())
    ConductReply.__doc__ = BASELINE

    print(f"scenarios: train={len(TRAIN)} val={len(VAL)} held-out={len(TEST)} (disjoint intents)\n")

    print("=== HELD-OUT baseline (the REAL shipping prompt) ===")
    b, t, lo, hi = eval_held(ConductAgent())
    print(f"baseline: {b}/{t}  ({100 * b // t}%, 95% CI {100 * lo:.0f}-{100 * hi:.0f}%)\n")

    print("=== GEPA optimizing (Nemotron task + reflection) ===")
    opt = dspy.GEPA(
        metric=metric, auto="light", num_threads=4, track_stats=True,
        reflection_lm=get_lm(temperature=1.0, max_tokens=2000),
    )
    compiled = opt.compile(ConductAgent(), trainset=TRAIN, valset=VAL)

    print("\n=== HELD-OUT optimized ===")
    b2, t2, lo2, hi2 = eval_held(compiled)
    print(f"optimized: {b2}/{t2}  ({100 * b2 // t2}%, 95% CI {100 * lo2:.0f}-{100 * hi2:.0f}%)")

    print(f"\n=== BOOKING RATE on HELD-OUT (unseen intents): "
          f"{100 * b // t}% -> {100 * b2 // t2}% ===")
    try:
        instr = compiled.turn.signature.instructions
        print("\n--- GEPA-optimized conduct prompt ---\n" + instr)
        open("optimized_prompt.txt", "w").write(instr)
    except Exception as e:
        print("(could not extract optimized prompt:", e, ")")


if __name__ == "__main__":
    main()
