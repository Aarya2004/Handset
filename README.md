# Handset 🤙

**Sign it. We'll say it. We'll handle the rest.**

A phone agent for people who can't speak into a phone. A Deaf or hard-of-hearing
user **signs at their webcam → the agent recognizes their signs → it places a real
phone call and _conducts_ it** — speaking their intent aloud to a hearing
receptionist, handling the receptionist's follow-ups, and bringing the replies
back as live captions. No human interpreter. No typing English as a second
language. No third person listening to your private calls.

> Code repo: **https://github.com/Aarya2004/Handset**
> Built at the YC Voice Agents Hackathon (Cekura × Daily/Pipecat × NVIDIA × AWS × Twilio), 2026-05-30.

---

## 1. What is this?

48 million Americans are Deaf or hard-of-hearing. When they need to call a clinic,
a pharmacy, or a front desk, today's options are bad: a **human relay interpreter**
sits in the loop on your most private calls (privacy gone, on their schedule, and
clinics hang up because relay calls sound like robocalls), or a text-relay app like
Nagish that makes you **type English** — a second language for the ~250–500k people
whose first language is ASL.

**Handset is a different category.** It's an autonomous voice agent that:

1. **Reads your signs on-device.** MediaPipe Hands tracks 21 hand landmarks in the
   browser; a **per-user k-NN classifier you teach in seconds** turns them into sign
   tokens. The classifier lives in *your* browser's `localStorage` (`signal_profile`)
   — nothing leaves the device, so it's private by construction and adapts to *your*
   hand shape instead of forcing a universal model.
2. **Conducts the call, doesn't relay it.** The recognized intent
   (`APPOINTMENT, T-H-U-R-S-D-A-Y`) goes to a **NVIDIA Nemotron** agent on a
   [Pipecat](https://pipecat.ai) pipeline that places a **real Twilio call** and
   speaks a natural sentence — *"Hi, I'm calling on behalf of a patient to book an
   appointment, would Thursday afternoon work?"* It identifies itself, fixes your
   fingerspelling, and answers the receptionist's pushback ("Is this a robocall?",
   "What's the patient's date of birth?") **without you signing anything new.**
3. **Brings the reply back as captions** — the hearing party's speech is transcribed
   by **NVIDIA Nemotron Speech ASR** and word-boosted against your personal lexicon so
   "Zoloft" never comes back as "so left."
4. **Improves itself.** We used **GEPA running entirely on Nemotron** to read *why*
   adversarial receptionists hung up and rewrite the agent's own prompt — then had
   **Cekura independently simulate and score** the before/after.

The whole pipeline — recognition, conduct, telephony, captions, and the
self-improvement loop — was built and tested end-to-end during the hackathon.

---

## 2. Demo video (< 60 seconds)

📹 **[ADD YOUR <60s VIDEO LINK HERE]**

> The video shows the *experience*: a person signs at the camera, says nothing, and
> a natural human-sounding voice books a real appointment on a live phone call while
> a skeptical receptionist pushes back — plus a few words on what we learned building
> it. (Required: keep it under 60 seconds.)

---

## 3. How we used Cekura, Nemotron, and Pipecat

We leaned on all three, hard. Here's the honest accounting of where each one lives.

### NVIDIA Nemotron — the brain, the ear, *and* the optimizer

Nemotron is on **every** intelligent surface of this project:

- **Conduct LLM (`nvidia/nemotron-3-super`, hosted on AWS).** The agent that turns
  signed intent into spoken sentences and conducts the multi-turn call
  (`server/handset_bot.py`, `CONDUCT_SYSTEM`). We hit a real gotcha here (see
  feedback): on the vLLM endpoint you **must** send
  `chat_template_kwargs: {enable_thinking: false}` or `content` comes back `null`.
  We run with thinking off for live-call latency.
- **Speech ASR (NVIDIA Parakeet / Nemotron Speech streaming).** A custom Pipecat
  `WebsocketSTTService` (`server/nvidia_stt.py`) transcribes the hearing party's
  replies into captions, then we apply **word boosting** (`server/lexicon.py`, pure
  `difflib`) — the sanctioned ASR-customization technique, done at the application
  layer — to snap meds/names/days to the user's canonical spelling. A mis-heard
  "Zoloft" in a medical call is the dangerous error; this fixes it.
- **Multimodal dynamic-sign tier (`nemotron-3-nano-omni-30b-a3b-reasoning`).**
  Static k-NN can't read *movement* signs (THANK-YOU, etc.). `client/recognizer.js`
  detects a motion burst, samples frames, and POSTs them to **Nemotron 3 Nano Omni**
  (the open multimodal model, via OpenRouter — `server/omni_recognizer.py`), which
  names the sign and feeds it back into the same conduct path. Omni's Conv3D
  "tubelet" embeddings capture motion *between* frames — exactly what a moving sign is.
- **GEPA reflection LM.** When we self-improved the agent (below), Nemotron was
  **both** the task model and the reflection model that rewrote the prompt.
  All-NVIDIA, end to end.

### Pipecat — the voice orchestration

The live agent (`server/handset_bot.py`, built on the starter's `bot-nemotron.py`)
is a Pipecat pipeline: a WebSocket sign-token transport in, Nemotron conduct,
Gradium TTS out to a **real Twilio outbound call**, and inbound audio → VAD →
Nemotron ASR → lexicon-boosted captions back to the signer's screen (a custom
`CaptionEmitter` FrameProcessor). Pipecat's frame model is what let us splice an
unusual input modality (sign tokens over WS) and a custom caption side-channel into
an otherwise standard telephony bot.

### Cekura — what we were testing, and how much we improved

**The goal in testing:** prove the agent gets *better at the calls that matter* —
completing a booking against **adversarial receptionists** — and prove it with an
**independent** judge, not our own homework.

**What we did:**

1. **Self-improvement with GEPA (on Nemotron).** We built a scenario bank split
   **disjoint by intent** (`server/optimizer/run_gepa.py`): train (`book
   appointment`), val (`refill prescription`), and a **held-out set of intents GEPA
   never sees** (`reschedule`, `get test results`). `dspy.GEPA` read the transcripts
   of calls that ended in `[HANGS UP]` — with a verifiable booked/hung-up reward —
   and autonomously rewrote the conduct prompt. It learned two concrete behaviors the
   naive prompt lacked: **(a) identify as a human assistant up front** (defeats
   robocall-skeptic / impatient personas) and **(b) proactively offer the patient's
   name + DOB** (clears the verification gatekeeper). On the held-out intents,
   booking went **~54% → ~70%**. We report Wilson 95% CIs and we're honest that they
   overlap at n=24 — so it's a real *generalization* point-estimate gain, not a
   significance claim.

2. **Cekura scored it independently.** We exposed both prompts over Cekura's
   WebSocket chat-test protocol (`server/cekura/conduct_ws.py`, `/baseline` vs
   `/gepa` from one process) and registered **two agents** in Cekura (Baseline
   #18061, GEPA #18062, project 5860). Cekura then **simulated four receptionist
   personas it scored itself** — *Robocall Skeptic, Impatient, Verification
   Gatekeeper,* and a *Cooperative control* — across **24 WebSocket calls** (12 per
   prompt; result IDs #591398 baseline, #591399 GEPA, all completed, zero call
   errors). The crucial point: **GEPA optimizes; Cekura simulates and scores. The
   optimizer and the judge are different parties.**

3. **An independent stress battery** (`server/cekura/stress_battery.py`) of 15
   adversarial personas, strict temp-0 Nemotron judge, `[BOOKED]`/`[REFUSED]` markers
   stripped before judging so the judge can't cheat. Honest result: GEPA shows a
   **small, consistent edge with lower variance** — across 3 runs (45 calls each)
   baseline booked **27/45 (10,9,8)** vs GEPA **30/45 (10,10,10)** — with clear wins
   on the adaptation/negotiation personas it was optimized for. Both still fail the
   hard-refuse personas ("no third-party calls"), which is an honest agent weakness,
   not a test artifact. We did not overclaim a dramatic robustness win.

So: **measure → diagnose why it failed → let the model rewrite itself → re-measure
with an independent judge.** That's the loop the hackathon asked for, and Cekura was
the independent scoring layer that made the gain credible rather than self-graded.

---

## 4. What we did *new* during the hackathon

Almost all of it. We started from the Pipecat **Field & Flower** flower-shop starter
in this repo (a voice ordering bot). Everything that makes Handset *Handset* was
built today:

**Built new today:**

- The entire **product concept** (ASL-in → conduct → real call → captions).
- **On-device sign recognition** — MediaPipe Hands + a **per-user k-NN** classifier
  with "teach a sign" enrollment (5-frame prototypes), confidence gating
  (accept ≥0.7 / ask-to-confirm ≥0.45 / reject), a velocity+handshape hold-to-commit
  gate, and pause-based sentence buffering (`client/recognizer.js`,
  `client/signal-room.html`).
- The **conduct agent** — reframing the starter bot from "take a flower order" to
  "place and conduct a call on a Deaf patient's behalf," with a verbatim hero-path
  `PHRASE` map for reliability and a Nemotron conduct path for everything else.
- **Real Twilio outbound calling** wired to the Pipecat media stream (the starter
  only documented *inbound* via TwiML Bin — outbound was custom work).
- **Caption-back** path: Nemotron ASR + **`lexicon.py` word boosting**.
- **Dynamic-sign tier** via Nemotron 3 Nano Omni (`server/omni_recognizer.py`).
- The **whole self-improvement + evaluation stack**: GEPA on Nemotron
  (`server/optimizer/`), the Cekura WebSocket bridge (`server/cekura/conduct_ws.py`),
  the two registered Cekura agents, the adversarial scenarios, and the stress battery.

**Borrowed / pre-existing:**

- The **Pipecat starter** (pipeline scaffold, Gradium STT/TTS wiring, Twilio inbound
  TwiML, Pipecat Cloud deploy config) — `bot-nemotron.py` was our starting point.
- **Pre-trained weights only**: MediaPipe Hands (landmark detection) and the Nemotron
  models. We *used* and *configured* the Nemotron models (word boosting,
  `enable_thinking`, GEPA reflection) but did not retrain them.

We deliberately did **not** train a sign model from scratch: real conversational ASL
recognition is an unsolved research problem (~61% top-1 on WLASL-2000), so the
trustworthy move was an on-device per-user classifier (private, adapts live) for
static signs + Omni for motion signs — and to put the genuine ML novelty in **the
agent's self-improvement loop**, which we *could* measure honestly in the time we had.

---

## 5. Feedback on the tools

### NVIDIA Nemotron

**What it did well:**

- **Conduct quality was genuinely good.** `nemotron-3-super` writes clean, natural,
  single-sentence receptionist-facing speech and handles multi-turn negotiation /
  verification well. The baseline was already strong, which made it a *fair* (hard)
  bar for the GEPA improvement.
- **It optimizes itself well.** As the GEPA reflection LM, Nemotron produced a
  coherent, well-structured rewritten prompt from raw failure transcripts — and its
  diagnoses (identify as human, proactively verify) were exactly right. Strong
  reflective reasoning.
- **Nano Omni's motion handling** (Conv3D tubelets) is conceptually the right tool
  for movement signs.

**What could be better:**

- **The `enable_thinking=false` gotcha cost us real time.** On the hosted vLLM
  endpoint, omitting `chat_template_kwargs: {enable_thinking: false}` returns
  `content: null` (the reasoning goes somewhere we never see), which looks like a
  broken endpoint. This deserves a louder note in the model card / cookbook — it's a
  silent footgun for a latency-sensitive voice app.
- **Text-only `nemotron-3-super` vs. the multimodal story.** The provided hosted LLM
  is text-only (`GET /models` → only `nemotron-3-super`; sending an image 400s with
  "not a multimodal model"). The only multimodal Nemotron (Nano Omni) wasn't on the
  provided infra, so we routed it through OpenRouter ourselves. A hosted Omni endpoint
  during the event would have unlocked a much stronger "model reads the sign directly"
  demo.
- **Reasoning token budget on Omni.** Nano Omni (reasoning variant) needed real token
  headroom or it returned `UNKNOWN` on signs — easy to misread as the model failing.

### Cekura — building self-improvement loops

**What worked really well:**

- **The WebSocket chat-test protocol is the right abstraction.** Because we could
  expose *any* agent over a WS endpoint (we served `/baseline` and `/gepa` from one
  process), Cekura could drive a self-hosted Nemotron agent it knew nothing about.
  That separation — *our* optimizer, *Cekura's* simulator + scorer — is exactly what
  made our before/after credible. For a self-improvement story, having the judge be a
  different party than the optimizer is the whole game, and Cekura made that easy.
- **Persona-driven adversarial simulation** mapped cleanly onto our problem (the
  receptionist *is* the adversary). Registering two agents and pointing them at the
  same scenario set for a side-by-side was straightforward.
- **The MCP + Claude Code skills** let us create agents, scenarios, and runs without
  leaving the terminal — fast iteration during a 6-hour build.

**Bugs / rough edges we hit:**

- **MCP list endpoints require an org/project id but don't say which call discovers
  it.** `aiagents_list` / `projects_list` 400 with *"provide one of project_id,
  organization_id"* — but a new user doesn't know `user_organizations_list` is the
  bootstrap call. The error could name the discovery call.
- **CEKURA_API_KEY / 401 onboarding friction.** Early in the day the MCP returned 401
  until credits/keys propagated; it blocked our eval work for a while. A clearer "your
  key isn't active yet" signal vs. a generic 401 would help.
- **`success_rate: 100%` / `success: true` means a run *completed* (reached terminal
  state), not that it *passed* the metric.** A connection that completed with zero
  bookings still reads as "100% success" at the result level. We get the distinction
  now, but it's an easy trap — surfacing metric-pass-rate alongside completion-rate at
  the list level would prevent misreading.

### Pipecat / Daily

- Splicing a **non-standard input modality** (sign tokens over WS) and a **custom
  caption side-channel** into a telephony bot was clean thanks to the frame model.
- The biggest friction was outbound Twilio (custom, not in the starter) + needing a
  public tunnel for the media stream — expected for telephony, but the starter
  documenting only inbound meant outbound was a from-scratch path.

---

## 6. Live link (optional)

🔗 **[ADD A LIVE LINK HERE IF YOU HAVE ONE]** — Handset runs locally
(`client/signal-room.html` + `server/handset_bot.py` on :8790 + a cloudflared tunnel
for Twilio). See **[Aarya2004/Handset](https://github.com/Aarya2004/Handset)** for run
instructions and `TEST_PROTOCOL.md` for the full end-to-end chain.

---

### Ethical note

ASL is a complete, natural language — not English on the hands. Handset is about
**autonomy and privacy** (removing the human who has to listen to your private
calls), not "fixing" anything about Deaf people. Deaf people aren't broken; the phone
system is. This is a hearing-built prototype, and a real product ships only with Deaf
leadership and Deaf co-design — *nothing about us without us.* Today's recognizer is
one-handed and scoped to a working appointment/pharmacy vocabulary (A–Z
fingerspelling + ~8 command signs); fluent conversational ASL is the roadmap, not a
claim we make.
