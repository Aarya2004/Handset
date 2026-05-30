"""
server/lexicon.py — WORD BOOSTING at the application layer.

This is the genuine Nemotron-ASR customization (NVIDIA's own sanctioned technique,
done at the layer the hosted endpoint exposes to us). It biases the hearing-side
transcript toward the user's PERSONAL lexicon — meds, names, days, places — so the
captions are right on the words that matter. A mis-heard "Zoloft" in a medical call
is the dangerous error; this fixes it.

The lexicon GROWS every call (the same per-user lexicon the sign-profile builds) =
Loop A auto-improvement. Pure stdlib (difflib), no deps, no keys — unit-testable.

Bot caption path:  caption = boost(asr_text, user_lexicon)
"""

import difflib
import re

_TOKEN = re.compile(r"^(\W*)([A-Za-z']+)(\W*)$")


def boost(transcript: str, lexicon: list[str], cutoff: float = 0.68) -> str:
    """Replace transcript words that closely match a personal-lexicon term with
    the canonical spelling. Preserves surrounding punctuation; canonical casing.
    Single-word terms (Zoloft, Thursday, Chen) — covers the medical/appointment
    demo vocabulary. Multi-word phrases are a future extension."""
    if not lexicon or not transcript:
        return transcript
    lex = {t.lower(): t for t in lexicon if t.strip()}
    keys = list(lex.keys())

    def fix(tok: str) -> str:
        m = _TOKEN.match(tok)
        if not m:
            return tok
        pre, core, post = m.groups()
        low = core.lower()
        if low in lex:                       # exact (case-insensitive) hit
            return pre + lex[low] + post
        cand = difflib.get_close_matches(low, keys, n=1, cutoff=cutoff)
        if cand:                             # fuzzy ASR-error hit
            return pre + lex[cand[0]] + post
        return tok

    return " ".join(fix(t) for t in transcript.split())


if __name__ == "__main__":
    cases = [
        ("i'll refill your zelloft on thirsday.", ["Zoloft", "Thursday"]),
        ("see doctor chen next week", ["Chen"]),
        ("your appointment is confirmed", ["Zoloft"]),   # must NOT false-positive
        ("take metoprolol daily", ["metoprolol"]),        # exact
        ("booked for wendsay at noon", ["Wednesday"]),    # fuzzy
    ]
    for txt, lex in cases:
        print(f"IN : {txt!r}  +{lex}")
        print(f"OUT: {boost(txt, lex)!r}\n")
