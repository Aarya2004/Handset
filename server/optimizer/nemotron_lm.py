"""Nemotron-3-Super as a dspy.LM — used as BOTH the task LM and the reflection LM
(end-to-end on NVIDIA open models, per the hackathon). enable_thinking=false is
mandatory or `content` comes back null."""

import dspy

NEMO_BASE = "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1"
MODEL = "openai/nvidia/nemotron-3-super"


def get_lm(temperature=0.4, max_tokens=200):
    return dspy.LM(
        MODEL,
        api_base=NEMO_BASE,
        api_key="EMPTY",
        temperature=temperature,
        max_tokens=max_tokens,
        model_type="chat",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


if __name__ == "__main__":
    lm = get_lm()
    dspy.configure(lm=lm)
    out = lm("Reply with one short sentence confirming you can hear me.")
    print("LM output:", repr(out))
    assert out and out[0].strip(), "EMPTY output — enable_thinking likely not applied"
    print("✅ dspy.LM → Nemotron works (non-empty)")
