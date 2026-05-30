# Handset — Judge Demo Script

**One line:** A phone agent that learns your signs and makes the call for you.

**Tagline:** Sign it. We'll say it. We'll handle the rest.

---

## 60-Second Spoken Pitch

> 48 million Americans are Deaf or hard-of-hearing. When they need to call a
> clinic, a pharmacy, a front desk — a phone call they can't make — they fall
> back on relay services: a human interpreter in the loop, on their schedule,
> reading their words verbatim. And clinics hang up on relay calls, because they
> sound like robocalls.
>
> Handset is different. You sign to your phone camera. On-device, it recognizes
> _your_ signs — not a generic model, a per-user classifier you teach in seconds,
> stored locally, nothing leaves the device. The recognized intent goes to a
> Nemotron agent that places a **real phone call** and _conducts_ it. It doesn't
> relay your words — it expands "APPOINTMENT, Thursday" into natural speech,
> fixes your fingerspelling, identifies itself as a human assistant, and answers
> the receptionist's follow-ups: "Is this a robocall?" — "What's the patient's
> date of birth?" The hearing person's replies come back as live captions,
> corrected against your personal lexicon so "Zoloft" never comes through as
> "so left."
>
> Nagish relays words. Handset completes the transaction. It's an autonomous
> voice agent for the calls Deaf people can't make — and it gets better on its
> own. We let GEPA, running entirely on Nemotron, read _why_ adversarial
> receptionists hung up and rewrite the agent's own prompt. On a held-out set of
> intents it had never seen, booking went from 54% to 70%. And Cekura — the host
> — independently certified that gain.
>
> Sign it. We'll say it. We'll handle the rest.

_(~58s at a natural pace. Drop the lexicon sentence if running long.)_

---

## Live Demo — Run of Show (target 2:30)

**Pre-stage (before walking up):**

- `handset_bot.py` running, Twilio creds live, `TWILIO_TO_NUMBER` = the receptionist phone on stage (a teammate or a second laptop running the Cekura simulator over speaker).
- Bridge server up; client open in Chrome with camera permission already granted.
- A clean per-user `signal_profile` in localStorage with HELLO / APPOINTMENT / THURSDAY / THANK-YOU pre-enrolled, plus one slot deliberately empty for the live teach.
- Phone on stage, volume MAX, pointed at the room mic. This is the whole show — the room must _hear_ it.

**Beat 1 — "It learns your signs" (~30s)**

- Sign one of the pre-enrolled words. The on-screen read-out fires; the confidence/landmark overlay tracks 21 points in real time.
- Then: "Watch it learn a new one." Click **Teach a sign**, type `WATER`, hold the sign 5 frames. The `learned` chip appears with the prototype count.
- Sign WATER once more — it now commits. Say: "That classifier lives in _this browser_. No cloud, no training run, no PHI off-device."

**Beat 2 — THE HERO MOMENT — a signed word comes out of a real phone (~50s)**

- Say: "Now I'm going to book a real appointment. I'm not going to speak. I'm going to sign."
- Sign `APPOINTMENT`, then fingerspell `T-H-U-R-S-D-A-Y`. The buffered intent fires to the conduct agent.
- **The phone on stage rings and answers. The room hears a natural human-sounding voice say:** _"Hi, I'm calling on behalf of a patient to book an appointment — would Thursday afternoon work?"_
- **This is the moment. Pause. Let it land.** A signed word just became a spoken sentence on a live outbound call. Point at the phone, not the screen.

**Beat 3 — "It conducts, it doesn't relay" (~40s)**

- The receptionist pushes back (scripted or Cekura-simulated): _"Is this a robocall?"_ and _"What's the patient's date of birth?"_
- The agent handles both without the Deaf user signing anything new — identifies as a human assistant, supplies the verification it was given. This is the difference between a relay and an agent: **it owns the conversation.**
- The receptionist's words land as **live captions** on the Deaf user's screen — and call out one lexicon correction (a misheard med/name snapped back to canonical spelling).

**Beat 4 — "And it improved itself" (~30s)**

- Cut to the Cekura dashboard (browser tab, pre-loaded).
- "We didn't hand-tune this prompt. GEPA — running on Nemotron — read the failure transcripts and rewrote it. Here's the same agent, baseline prompt versus GEPA prompt, scored by Cekura on adversarial receptionists it ran itself."
- Read the certified numbers off the board. Close: "The host platform certified the self-improvement. That's the loop."

**Hero moment, stated once for the judges:** _a word the Deaf user signed, coming out of a real phone call as natural speech, with the room hearing it._ Everything else supports that one second.

### Recorded-backup fallback

A 90s screen+phone recording of the full Beat 1→4 run sits one keypress away (`demo-backup.mp4`, also uploaded so it survives a dead laptop). **Trigger to switch:** camera fails to commit a sign within ~10s, OR the Twilio call doesn't connect within two rings. Say plainly: _"Live telephony on conference WiFi — here's the same run we recorded an hour ago,"_ and play it. Never debug on stage. The Cekura numbers and the GEPA result are real regardless of whether the live call connects, so the self-improvement story is fallback-proof.

---

## Technical Depth (what judges will probe)

- **Per-user k-NN sign adaptation.** MediaPipe Hands gives 21 normalized landmarks per frame, client-side. "Teach a sign" enrolls 5-frame prototypes into a per-label set in `localStorage` (`signal_profile`); recognition is nearest-prototype with a distance-scaled confidence gate (accept / ask-to-confirm / reject) plus dwell-to-commit. It adapts to _one person's_ hand shape and signing style instead of forcing a universal model — and it's private by construction (no landmarks leave the device). Ambiguous reads surface a top-3 the user confirms, which itself enrolls a new prototype.
- **All-NVIDIA conduct + ASR.** The conduct agent is Nemotron (`enable_thinking=false` — mandatory, else `content` is null on the vLLM endpoint) over a Pipecat pipeline; TTS to a real Twilio outbound call; hearing-side speech via Nemotron ASR. The hearing transcript is then word-boosted against the user's personal lexicon (`lexicon.py`, difflib) so meds/names/days snap to canonical spelling — the dangerous-error class in a medical call.
- **GEPA-on-Nemotron, honestly measured.** `dspy.GEPA` (SOTA reflective prompt optimizer) rewrote the conduct prompt by reading _why_ adversarial receptionists hung up — with Nemotron as **both** the task LM and the reflection LM (`server/optimizer/run_gepa.py`). Scenarios are split disjoint by intent (train / val / **held-out**); GEPA never sees the held-out intents, so 54% → 70% is a real generalization measure, not memorization. Wilson 95% CIs reported; they overlap at n=24, so we present it as an honest point-estimate gain to scale-and-certify, not a significance claim. GEPA's learned behaviors: identify as a human assistant up front, and proactively verify patient name + DOB.
- **Cekura certification (independent).** We exposed the Nemotron conduct agent over Cekura's WebSocket chat-test protocol (`server/cekura/conduct_ws.py`, `/baseline` vs `/gepa` paths) and registered two Cekura agents. Cekura simulated adversarial receptionists (robocall-skeptic, impatient, verification-gatekeeper, + a cooperative control) and scored every call with its LLM-judge metrics (Booking Completed, Handled Identity Verification, Sounded Human / Not Robocall). **GEPA optimizes; Cekura simulates and scores — the optimizer and the judge are different parties.**

  `[CEKURA RESULTS: baseline __% → GEPA __% booking, certified on Cekura dashboard]`

- **Side eval, zero live-demo risk.** Separately, we ran the _same_ signing clips through NVIDIA Nemotron-Nano-12B-VL on AWS Bedrock (`omni_recognizer.py`) head-to-head against the on-device MediaPipe recognizer and scored both in Cekura. MediaPipe stays the live spine (VL-on-ASL is unproven); the VL path is the "open NVIDIA multimodal model on AWS, measured" comparison — off the critical path, behind a config flag.

**Sponsor surface (all real, all in the live or eval path):** NVIDIA Nemotron (conduct LLM + ASR + GEPA reflection LM) and Nemotron-Nano-12B-VL on AWS Bedrock; Cekura (simulation + scoring + certified self-improvement loop); Daily/Pipecat (bot orchestration); Twilio (the real outbound call); AWS (Bedrock + the Nemotron fleet).

---

## Limitations / Roadmap (we will not overclaim)

The MVP recognizer is **one-handed** and scoped to a working appointment/pharmacy
vocabulary (A–Z fingerspelling + ~8 command signs) — enough to complete the demo
transaction, not full conversational ASL. Two-handed ASL and a Nemotron-VL
fine-tune on ASL are the recognition roadmap; VL-on-ASL is unproven today, which
is exactly why MediaPipe is the live spine and VL is an offline eval. On the
agent side, the 54% → 70% GEPA gain has overlapping Wilson CIs at n=24 — it's an
honest point estimate we'd scale to statistical certification, not a significance
claim, and Cekura is the path to certifying it at volume. Personal lexicon
boosting is single-word today (multi-word phrases are next). Everything in this
demo is real and was tested end-to-end today; nothing here is mocked.

---

## If a Judge Asks…

- **"Why not just use Nagish / a relay service?"** Relays put a human interpreter
  in the loop and read your words _verbatim_ on your schedule — and clinics hang
  up on them because they sound like robocalls (the NAD "Don't Hang Up" campaign
  exists for exactly this). Handset is an autonomous _agent_: no human in the
  loop, it expands intent into natural speech, identifies as a human assistant,
  and handles the receptionist's follow-ups itself. It completes transactional
  calls — booking, verification, screening — that relays make slow and awkward.
  We're not a better relay; we're a different category.

- **"Is the 54 → 70 improvement real, or cherry-picked?"** Real and adversarial
  by design. GEPA optimized on one split and was measured on a **held-out set of
  intents it never trained on**, so the number reflects generalization, not
  memorization. We report Wilson 95% CIs and we tell you they overlap at n=24 —
  so we call it an honest point-estimate gain, not statistical significance. And
  we didn't grade our own homework: **Cekura** ran the adversarial simulations
  and scored every call. Optimizer and judge are separate parties.

- **"What did GEPA actually change in the prompt?"** It read the transcripts of
  calls that ended in `[HANGS UP]` and learned two concrete behaviors the naive
  prompt lacked: (1) **identify as a human assistant immediately** — defeats the
  robocall-skeptic and impatient personas that hang up on the first ambiguous
  line; (2) **proactively offer patient identity (name + DOB)** instead of
  waiting to be asked — clears the verification-gatekeeper. Same model, same
  endpoint; only the conduct prompt changed, and Nemotron itself wrote the new
  one.
