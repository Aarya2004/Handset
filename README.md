# Handset 🤙

**Sign it. We'll say it. We'll handle the rest.**

A Deaf/HoH user **signs at their webcam → an agent recognizes the signs → it places a
real Twilio phone call and *conducts* it** (speaks the intent, handles the
receptionist's follow-ups), and the replies come back as live captions. No human
interpreter. No typing English as a second language.

> Code: **https://github.com/Aarya2004/Handset** · Built at the YC Voice Agents Hackathon, 2026-05-30.

---

## 1. What is this?

Deaf people can't make routine calls (clinic, pharmacy, front desk) without a **human
relay interpreter** listening to their private calls (e.g. See here https://www.youtube.com/shorts/2K80exBAe_E)
or typing English, a second language for the ~250–500k ASL-first users. Handset is an autonomous voice agent
instead. The pipeline, end to end:

```
sign (camera) → recognizer.js (per-user k-NN, on-device) → WS {sign tokens}
   → handset_bot.py → Nemotron conduct / Nemotron Omni (intent/sign → sentence) → Gradium TTS
   → Twilio outbound call → receptionist answers & talks back
   → Nemotron ASR + lexicon boost → caption back to the signer's screen
```

It **conducts, it doesn't relay**: it expands `APPOINTMENT, T-H-U-R-S-D-A-Y` into
*"Hi, I'm calling on behalf of a patient to book an appointment, would Thursday
afternoon work?"*, identifies as a human assistant, and answers "Is this a
robocall?" / "What's the patient's DOB?" — **without the user signing anything new.**

## 2. Demo video (< 60s)

📹 **https://drive.google.com/file/d/1TTeO1lfBQuNXYKoC5nmG94CeMm53WGfy/view?usp=sharing**

## 3. How we used Cekura, NVIDIA, AWS & Pipecat

### NVIDIA

- **Conduct LLM** (`nemotron-3-super`, hosted on AWS) — turns signed intent into
  spoken sentences and conducts the multi-turn call.
- **Speech ASR** (NVIDIA Parakeet / Nemotron streaming) via a custom Pipecat
  `WebsocketSTTService` (`nvidia_stt.py`), then **word boosting** (`lexicon.py`,
  `difflib`) snaps meds/names/days to the user's canonical spelling (e.g. "Zoloft" not
  "so left").
- **Nano Omni** (`nemotron-3-nano-omni-30b`, multimodal, via AWS) reads
  *motion* signs that static k-NN can't (`omni_recognizer.py`): `recognizer.js`
  detects motion → POSTs a burst of frames → Omni names the sign → same conduct path.
- **GEPA reflection LM** — Nemotron is **both** the task and reflection model in the
  self-improvement loop (described below).

### Gradium (TTS)

- The natural voice the receptionist hears on the live Twilio call is **Gradium TTS**
(`GradiumTTSService`): it's the voice of the agent in the demo.

### Pipecat (orchestration)

- `handset_bot.py` (built from the starter's `bot-nemotron.py`): a websocket sign-token transport in,
Nemotron conduct, Gradium TTS → real Twilio outbound call, and inbound audio → Voice Activity Detection →
Nemotron ASR → lexicon-boosted captions back via a custom `CaptionEmitter`
FrameProcessor. The frame model is what let us splice a non-standard input modality
and a caption side-channel into a standard telephony bot.

### Cekura (independent eval + the self-improvement loop)

- **Goal:** prove the agent gets better at *completing a booking against adversarial
receptionists*, scored by an **independent** judge. We used **GEPA (on Nemotron)** to
rewrite the agent's own conduct prompt from its failure transcripts
(held-out booking **54% → 70%**), and registered both prompts as Cekura
agents (**Baseline #18061 / GEPA #18062**, project 5860) so **Cekura** could
independently simulate adversarial receptionists and score every call with its own
multi-metric rubric. **GEPA optimization, Cekura evals.**

(**Full technical write-up of this loop is §4 below**).

## 4. The self-healing loop, in depth

### 4a. Loop 1: GEPA rewrites the conduct prompt (offline, all-Nemotron)

`server/optimizer/` runs `dspy.GEPA`, a reflective prompt optimizer, with **Nemotron
as both the task LM and the reflection LM** , so the agent that *makes* the calls and
the agent that *reads the failures and rewrites the prompt* are the same open model.

- **Environment = adversarial receptionists as code.** `gepa_conduct.py` defines a
  `ConductAgent` (the agent under test) and a set of receptionist `PERSONAS`
  (robocall-skeptic, impatient, verification-gatekeeper). Each persona is a Nemotron
  call that runs the multi-turn dialogue and **emits a machine-checkable terminal
  token: `[BOOKED]` or `[HANGS UP]`.**
- **Verifiable, un-gameable reward.** The metric is *not* an LLM judging vibes: it's
  `1.0 if "[BOOKED]" in transcript else 0.0`, parsed from the receptionist's own
  terminal token, with the **hang-up reason fed back as the textual feedback** GEPA
  reflects on. (Contrast with Loop 2, where the *separate* party Cekura applies LLM
  judges, see 4c.)
- **Honest generalization split.** Scenarios are **disjoint by intent**: GEPA trains
  on `book appointment`, validates on `refill prescription`, and is measured on a
  **held-out set of intents it never sees** (`reschedule`, `get test results`). So the
  number reflects transfer, not memorization.
- **What GEPA actually learned.** Reading the `[HANGS UP]` transcripts, Nemotron
  rewrote the conduct prompt to **(a) identify as a human assistant up front** (kills
  the robocall-skeptic / impatient hang-ups) and **(b) proactively volunteer the
  patient's name + DOB before being asked** (clears the verification-gatekeeper). The
  rewritten prompt is checked in as the artifact: `optimizer/optimized_prompt.txt`.

### 4b. Loop 2: Cekura is the independent grader (online, on the dashboard)

We then handed the *same two prompts* to Cekura so a **different party** could
simulate and score them. TLDR: the optimizer (GEPA) and the judge
(Cekura) are not the same system.

- **Both arms registered as real Cekura agents** (project 5860):
  `Handset Conduct — Baseline` (**#18061**) and `Handset Conduct — GEPA` (**#18062**),
  both **Custom provider over WebSocket**. One process (`cekura/conduct_ws.py`) serves
  both: path `/baseline` loads the shipping `CONDUCT_SYSTEM`, `/gepa` loads
  `optimized_prompt.txt`. Cekura plays the receptionist; our Nemotron agent is the
  agent-under-test and speaks first.
- **Cekura simulated 4 receptionist personas**: Robocall Skeptic, Impatient,
  Verification Gatekeeper, and a Cooperative control, across **24 WebSocket calls**
  (results **#591398** baseline / **#591399** GEPA).

**The eval rubric we authored in Cekura (this is the technical heart):**

We wrote **3 custom Boolean LLM-judge metrics**, each scoped to a Handset-specific
failure mode, plus enabled Cekura's predefined voice metrics: **15 metrics total**,
all `Always`-triggered, on both Observability and Simulation:

| ID | Custom metric | Scores TRUE iff… |
|----|---------------|------------------|
| **147891** | Booking Completed | by end of call the receptionist actually booked / locked in the appointment |
| **147892** | Handled Identity Verification | when asked, the agent gave **both** the patient's full name (Jordan Lee) **and** DOB (March 3 1990) clearly — FALSE if it dodged |
| **147893** | Sounded Human / Not Robocall | the agent came across as a real, purposeful human caller a spam-wary receptionist would *not* dismiss |

These map 1:1 onto exactly what GEPA was optimizing (booking, verification,
human-not-robocall), so Cekura is scoring the *same behaviors* from an independent
seat. Alongside them we use Cekura's predefined surface: `Latency (ms)`,
`Interruption Score`, `Stop Time after User Interruption`, `Tool Call Success`,
`Transcription Accuracy`, `Unnecessary Repetition Score`, `Talk Ratio`,
`AI interrupting user`, etc.

**The success gate is a real rubric, not a single score.** In Cekura's Rubric
(success/failure config) a call is marked successful **only if every condition
passes** (conditions set to *None* are skipped):

```
Expected Outcome              = True
Infrastructure Issues         = True      (i.e. no infra failure)
Interruption Score            ≥ 1
Latency (ms)                  ≤ 10000
Stop Time after Interruption  ≤ 10000 ms
Tool Call Success             = True
Transcription Accuracy        ≥ 1
Unnecessary Repetition Score  ≥ 2.5
```

This is the conjunctive, multi-metric definition of "a good call", it's what lets
Cekura grade the agent on conversation *quality* (latency, repetition, interruption
handling, transcription), not just the binary booking.

### 4c. What the loop actually caught (the honest part)

- **On the 4-persona run, both arms booked 100%, the task was saturated**, so that
  Cekura run is evidence we *evaluate independently with Cekura*, **not** a booking
  climb on the dashboard. The booking climb is the held-out GEPA number in 4a.
- **Cekura's grading *did* catch a real, live behavior bug** the booking-only metric
  missed: the agent **replying** to a signed `THANK-YOU` with *"You're welcome!"*
  (chatbot mode) instead of **voicing** *"Thank you"* as the signer. We hardened
  `CONDUCT_SYSTEM` ("you ARE the caller, never reply") and re-verified. That's the
  loop working: **measure → catch a failure a human would've shipped → fix.**
- **Harder coverage via an independent stress battery** (`cekura/stress_battery.py`):
  15 adversarial personas, temp-0 Nemotron judge, with `[BOOKED]`/`[REFUSED]` markers
  stripped before judging so the judge can't cheat. Across 3 runs of 45 calls,
  **baseline 27/45 → GEPA 30/45**, a small, consistent edge with **lower variance**,
  clear wins on the negotiation personas GEPA was optimized for; both arms reliably
  fail the hard-refuse personas (no-third-party-calls), a real agent limitation, not
  a test artifact.

**Net:** GEPA closes the *optimization* loop on Nemotron with a verifiable reward;
Cekura closes the *validation* loop from an independent seat with a real multi-metric
rubric and between them they produced one measured generalization gain (54→70) and
one caught-and-fixed production bug, all during the hackathon.

## 5. What's new during the hackathon

Everything (ASL-in → conduct → real call → captions) was built today on the Pipecat **Field & Flower** flower-shop starter. Specifically:

- **On-device sign recognition**: MediaPipe Hands + per-user **k-NN** with
  teach-a-sign (5-frame prototypes), confidence gates (accept ≥0.7 / ask ≥0.45 /
  reject), velocity+handshape hold-to-commit, pause-based sentence buffering
  (`recognizer.js`, `signal-room.html`).
- The **conduct agent** (reframed from "take a flower order" to "conduct a call on a
  Deaf patient's behalf").
- **Real Twilio outbound** wired to the Pipecat media stream (starter only documented
  inbound).
- **Caption-back** + `lexicon.py` word boosting; **Nano Omni** motion tier
  (`omni_recognizer.py`).
- The entire **GEPA-on-Nemotron + Cekura self-improvement/eval stack**
  (`optimizer/`, `cekura/`, the two registered agents, scenarios, stress battery).

## 5b. What we learned

A few things that surprised us building this:

- **Movement is the signal, not the pose.** Static k-NN on a single frame can't tell
  PLEASE from THANK-YOU, they share a handshape and differ only in *motion*. Letting
  k-NN commit those was our biggest source of wrong reads. The fix: route movement
  signs to the VLM (which sees the whole trajectory) and never let a single-frame
  classifier decide them.
- **Reasoning models need a token budget and an empty-content fallback.** Nemotron
  Omni burns hundreds of tokens *thinking* before it answers; too small a `max_tokens`
  and `content` comes back empty. We had to bump the budget and fall back to the
  reasoning field.
- **An ambiguous read should never reach a live phone.** We added a confirm-before-speak
  gate, mid-confidence signs surface a guess and wait, so a misrecognition can't get
  spoken on a real call to a real person.

## 6. Feedback

**NVIDIA Nemotron**: *Good:* `super` writes clean natural conduct speech and handles
multi-turn negotiation/verification; as the GEPA reflection LM it produced a coherent
rewrite with exactly-right diagnoses; Nano Omni's Conv3D motion handling fits sign
language. *Could be better:* omitting `chat_template_kwargs:{enable_thinking:false}`
**silently returns `content:null`** a real footgun, flag it louder in the card; the
hosted LLM is text-only (`GET /models` → only `super`; images 400), we also got confused
with the Nvidia 12B VLM (hosted on AWS Bedrock) so we started off a bit wrong. However, we did
fix our mistake after so we managed to finally get a hosted version of Nvidia Omni.

**Cekura** (self-improvement loops): *Good:* the WebSocket chat-test protocol is the
right abstraction, we exposed a self-hosted Nemotron agent it knew nothing about, and
the optimizer-vs-judge separation is what made our gain credible; persona-driven
adversarial sim maps perfectly onto "the receptionist is the adversary"; the MCP +
Claude Code skills let us create agents/scenarios/runs from the terminal. *Bugs:* list
endpoints 400 for an org/project id but don't say `user_organizations_list` is the
bootstrap call; early 401s before keys propagated (a generic 401 vs "key not active
yet"); **`success_rate:100%`/`success:true` means *completed*, not *passed***, a run
that booked nothing still reads as 100% success, an easy misread.

**Pipecat / Daily**: frame model made splicing sign-tokens + a caption side-channel
clean; main friction was outbound Twilio (custom, not in starter) + the public tunnel
for the media stream.

---

*ASL is a complete language, not English on the hands. This is about autonomy and
privacy, not "fixing" anyone a hearing-built prototype that ships only with Deaf
co-design. Today: one-handed, appointment/pharmacy vocab; fluent ASL is the roadmap.*
