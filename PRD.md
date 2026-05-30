# ASL Phone Agent — Build-Ready PRD

**Codename: SIGNAL ROOM** · YC Hackathon · v1.0 (locked) · ~5h to submission

---

## 1. One-liner + The Wow

**One-liner:** An autonomous ASL phone agent — a Deaf user signs to their camera, and a voice agent speaks their intent onto a *real* phone call to a hearing person, with the reply returned as live captions. No human interpreter. No typing in a second language.

**The demo sentence (the hero moment):**
> *"I sign to my phone — and it speaks to Aarya, on a real phone call, what I'm trying to say."*

**The closing line (the wow, lands last):**
> *"For the first time, this call had no human interpreter listening in."*

---

## 2. Problem & Users + Ethical Framing

### The wound
Today, when a Deaf person makes a phone call, a **third human — a Video Relay Service interpreter — listens to their most private conversations**: doctor's appointments, bank calls, legal matters. That is the wound the Deaf community names directly: *"a third person listening to my calls."*

### Killer stats (use on stage)
- **$1.5B/year** — the FCC Telecommunications Relay Service (TRS) fund, paying humans to relay Deaf people's calls.
- **50:1** — the interpreter shortage ratio; hold times and rationed access are the norm.
- **~250,000–500,000** ASL-primary users in the US for whom written English is a *second language* — so "just type it" (the Nagish model) is not autonomy.

### Users
Primary: ASL-first Deaf adults who must make routine phone calls (pharmacy, clinic, front desk, bank) and today either wait for a human interpreter or type English they're not fluent in.

### Ethical framing — EXACT WORDS

**USE on stage (open with the first one — sentence #1):**
- *"We're hearing builders. This ships only with Deaf leadership and Deaf co-design. Nothing about us without us."*
- *"ASL is a complete, natural language — not English on the hands."*
- *"Today, a phone call means a third person — a human interpreter — listens in. We remove that person."*
- *"This is about autonomy and privacy: your call, your language, no human eavesdropper."*
- *"We're not fixing anything about Deaf people. Deaf people aren't broken. We're fixing a broken phone system."*
- *"The sign processing runs on-device. The user signs their intent, in their own language."*

**AVOID — never say:**
- "cure," "fix," "restore," "help them hear," "give them a voice," "suffering," "impaired" (as a noun), "overcome their disability."
- Never call ASL "gestures," "signing English," or a simplified visual English.
- Never "the deaf" — say *"Deaf people"* / *"the Deaf community."*
- No savior pose ("we built this FOR them"), no hearing person signing badly as a punchline.
- Do **not** say *"only two people on the call"* (there's a cloud pipeline). Say *"no human interpreter listening."*

**Do this:** Get even 10 minutes of real Deaf ASL-user input before the demo and cite it: *"We showed this to a Deaf ASL user and they said ___."* Worth more than any latency number to this audience.

---

## 3. The Product + What Makes It NEW

A Deaf user signs to their laptop camera. On-device MediaPipe recognizes fingerspelling (A–Z) plus a small command vocabulary. A Pipecat voice agent **speaks their intent** onto a real Twilio phone call to a hearing party — and the hearing party's spoken reply is transcribed by Nemotron ASR and returned as **giant live captions**. Crucially, it is *not* a word-for-word relay: the agent **conducts** the call — expands sparse signed intent into natural speech, can navigate a phone tree, hold, and handle back-and-forth — so the user signs *intent*, not every word. No human interpreter, no typing in a second language. On a phone the user already owns.

### White space (vs. prior art)
- **Nagish ($16M):** autonomous AI relay, real calls, no human — but **TEXT-ONLY**. Ignores that ASL is the native, faster, emotionally-fluent language. Typing English ≠ autonomy in your own language.
- **Sorenson "Sign Language AI":** has real ASL recognition but aims at **in-person kiosks**, is POC-stage, and is structurally conflicted by its human-VRS revenue. Not consumer phone autonomy.
- **Google SignGemma:** a model, not a product. No telephony, no agent, no call orchestration.
- **VRS incumbents (Purple/ZVRS/Convo):** *are* the wound — a human always listening, supply throttled, business model hostile to automating itself away.

**Nobody fuses all three layers:** (a) ASL input + (b) an agent that *conducts* the call (intent, not transcript) + (c) a real two-way Twilio call with captioned replies. The novelty is the **fusion + agent autonomy**.

---

## 4. Novelty Score + The 3 Ways It Fails

**Novelty: 8.7 / 10.** A systems-integration + agent-autonomy novelty (every component exists), not new physics — but the *specific fusion* is shipped by no one. The defensible wedge is the **agent conducting the call** (intent, not transcript). **The demo must show the agent doing something a relay can't** (expanding sparse intent into a full sentence, or surviving a hostile "is this a robocall?").

| # | How it fails | Mitigation |
|---|---|---|
| 1 | **Recognition is too brittle live** — stage lighting/angle misfires, agent speaks garbage. | Scoped, rehearsed high-confidence vocab; confidence gate (only speak above threshold); fixed phrase allowlist (gesture → canonical string); clip-on fill light + dark sleeves + dark background; staged-input hotkeys `1–8` as silent insurance; recorded backup. |
| 2 | **Deaf community reads it as a hearing "fix."** Signing-glove backlash, appropriation risk (hearing person signing on stage). | Open with "nothing about us without us"; ASL = full language; commit to Deaf-led roadmap on stage; sign cleanly + minimally; cite real Deaf-user input. Lead privacy/autonomy, never the medical frame. |
| 3 | **Too many moving parts break live** (browser + Pipecat + Twilio + Nemotron + TTS) — the April-23 lesson. | ONE polished path (sign→speak→caption); prove the browser↔bot bridge with a `<button>` *before* wiring gestures; verbatim fixed strings on the critical path; mandatory full-loop recorded backup on the venue network as a hard go/no-go gate. |

---

## 5. Scope — MVP IN vs CUT (decisive)

### THE ONE FEATURE THAT MUST WORK
**Browser MediaPipe → committed sign → `sendClientMessage` → `TTSSpeakFrame` → Twilio call → Aarya hears it.** If only this works, there is a demo.

### IN (build, polish — in priority order)
1. **MediaPipe Hands in-browser** with live landmark overlay (the "it sees me" proof).
2. **A–Z fingerspelling + ~8 whole-sign command gestures** (HELLO, YES, NO, APPOINTMENT, CANCEL, THANK-YOU, REPEAT, WAIT) via **k-NN over normalized landmarks**.
3. **Committed sign → spoken onto the Twilio call.** Hero path = **verbatim fixed string**, `append_to_context=False`, **LLM not invoked**.
4. **Real Twilio two-way call to Aarya;** her reply → Nemotron ASR → server→client message → **big captions**.
5. **Enrollment ("teach a sign"):** capture 3 held frames of a new gesture → **new chip appears in Sign Profile** (the honest self-improvement beat — a guaranteed class-addition, not neural training).
6. **Recognition-latency HUD** — *measured* sign-commit-to-on-screen time + **Sign Profile** panel.
7. **One Nemotron "it conducts" beat** (intent token → Nemotron generates the full sentence → spoken) — **only if the bridge is proven by the 3h mark**, else fall back to verbatim.
8. **One Cekura eval card** — pre-baked before/after, shown as a static card.

### CUT (say no — protect the 5 hours)
- ❌ Signing avatar (Hand Talk / Sign-Speak) — flagged, not built.
- ❌ Open-vocab continuous ASL→English; HuggingFace WLASL models; pushing video INTO Pipecat.
- ❌ Any hosted sign API as load-bearing.
- ❌ **Live-climbing accuracy curve as load-bearing proof** (theater — cut; at most a static decorative sparkline).
- ❌ Live Cekura retraining; inbound calls; multi-user; accounts; mobile-native build.
- ❌ react-three-fiber / particle fields.
- ❌ **Fabricated telemetry** (jittering fake ms, synthetic "data" waveform) — measure for real or label as spec.

**On time pressure, cut in this order:** Cekura live → Nemotron intent-expansion → accuracy sparkline → enrollment re-recognition firing (keep the chip).

---

## 6. Architecture + Honest Latency Budget

### End-to-end data flow (every sponsor's box)

```
              DEAF USER (Arav)                                    HEARING PARTY (Aarya)
                    |                                                     |
            signs into camera                                      speaks into phone
                    v                                                     ^
   +----------------------------------------+                            |
   |  BROWSER CLIENT  (separate process)    |                            |
   |  MediaPipe Hands — local, no GPU       |                            |
   |  A-Z fingerspelling + ~8 gesture cmds  |                            |
   |  k-NN over NORMALIZED landmarks        |                            |
   |  + Sign Profile (localStorage)         |                            |
   |  -> emits COMMITTED SIGN TOKEN         |                            |
   +----------------------------------------+                            |
                    |                                                     |
        sendClientMessage  { token }                                    |
                    v                                                     |
 ========================= AWS us-west-2 ==============================|========
 |                                                                     |      |
 |  +--------------------- PIPECAT BOT (spine) ----------------------+ |      |
 |  |  on_client_message(token)                                     | |      |
 |  |       |                                                       | |      |
 |  |       |  HERO path: token -> fixed string  (no LLM)           | |      |
 |  |       |  CONDUCT path: token -> [NVIDIA Nemotron-3-Super]     | |      |
 |  |       |       enable_thinking=false ; intent -> sentence      | |      |
 |  |       v                                                       | |      |
 |  |  task.queue_frame( TTSSpeakFrame(text,                        | |      |
 |  |                    append_to_context=False) )  [Cartesia TTS] | |      |
 |  |       |                                  ^                    | |      |
 |  |       | (TTS audio out)                  | (ASR text in)      | |      |
 |  |       v                                  |                    | |      |
 |  |  +------------- TWILIO transport (Media Streams) ----------+  | |      |
 |  |  |  outbound audio  ========================================|==|===> RINGS
 |  |  |  inbound  audio  <======================================|==|==== speech
 |  |  +--------------------------------------------------------+  | |      |
 |  |       ^                                                      | |      |
 |  |       |  [NVIDIA Nemotron Speech Streaming ASR]  <-- the EAR | |      |
 |  |       |   ws://44.241.251.184:8080  transcribes hearing party| |      |
 |  |       |                                                      | |      |
 |  |  server->client message (caption text) ---------------------+ |      |
 |  +---------------------------------------------------------------+ |      |
 ====================================================================|========
                    v
   +----------------------------------------+
   |  BROWSER CLIENT — BIG LIVE CAPTIONS     |  <-- Deaf user reads the reply
   +----------------------------------------+

  --- OFFLINE / PRE-BAKED: CEKURA -------------------------------------------
  Adversarial hearing-party personas ("is this a robocall?", impatient IVR,
  fast talker) -> score the Pipecat agent -> v0 naive opener vs v1 hardened
  opener -> BEFORE/AFTER card. ONE live adversarial call survives on stage.

  AWS also: S3/CloudFront recorded-backup video. Whole runtime co-located in
  us-west-2 next to the NVIDIA endpoints for sub-second round-trip.
```

### Honest latency budget — present as TWO numbers

| Leg | Realistic | Note |
|---|---|---|
| MediaPipe per-frame inference | 8–20 ms | Local; not the bottleneck. |
| **Sign-commit dwell/debounce** | **150–250 ms** | Deliberate (tuned UP for zero false fires). Dominates the *recognition* number. |
| Client→bot WebSocket | 10–40 ms | Same-region, negligible. |
| LLM (conduct path only) | 0 or ~300 ms | **0 on the hero verbatim path.** |
| **Cartesia TTS time-to-first-byte** | **40–190 ms** | Cartesia Sonic — lowest available; beats Gradium. |
| Pipecat→Twilio injection | 20–50 ms | |
| Twilio→PSTN→Aarya's phone + jitter buffer | 200–500 ms | Slowest, least controllable leg. |
| **Return: Aarya speaks → ASR → caption** | **~0.5–1.0 s** | Budget it; use the lag as conversational rhythm. |

**The two HUD numbers (both true, both eye-verifiable):**
- **BIG (cyan): `RECOGNITION: ~220 ms`** — *measured with `performance.now()`* from sign-commit to on-screen token. Real, never fabricated.
- **Secondary: `SPOKEN TO CALLER: ~0.9 s`** — labeled honestly *"includes the live phone network."*

**The line to say:** *"My sign is recognized in about a fifth of a second. It reaches Aarya in under a second — and there's no third person on the line."* Lead with **autonomy/privacy**; treat speed as secondary. Do **not** stake the pitch on an unsourced "faster than a human interpreter."

**Critical technical guardrail — the `append_to_context` double-speak bug:** an injected `TTSSpeakFrame` *plus* an active LLM context can make the LLM also generate a reply → the agent talks over itself onto the live call. **Resolution: one path per utterance.** Hero = fixed string, `append_to_context=False`, LLM not invoked. Conduct = Nemotron is the sole *producer* of the utterance; the pipeline must not auto-respond to the user turn. **Test both paths in isolation in the first hour.**

---

## 7. The Self-Improvement Loop (the STAR + the support)

The hackathon theme: *"auto-improve — evaluation data flows back into the agent to improve over time."* We ship **two** loops; **one** is the star.

### STAR — Personal Sign Adaptation (the demo beat)
**Why novel (9/10):** Every prior system trains *one generic model for all signers* — and the Deaf community's exact critique is *"it doesn't understand MY signing"* (idiolect, regional dialect, handshape variance). **Nobody ships per-user, on-device, zero-training ASL personalization.** "It learns *me*" is the differentiator — and it doubles as the ethics frame (your signing, your device, no third human).

**Mechanism — no model training, no GPU, no backend:**

```
SignProfile = {
  userId: string,
  prototypes: { [token: string]: Float32Array[] },   // 63-dim normalized landmark vectors
  meta: { count, lastUpdated }
}                                                     // persisted to localStorage as JSON
```

**Feature vector (load-bearing):** MediaPipe → 21 landmarks × (x,y,z) = **63 floats/hand**. Normalize before storing/comparing or it won't generalize:
1. **Translate:** subtract wrist (landmark 0) → wrist-relative.
2. **Scale:** divide by wrist→middle-finger-MCP distance → size-invariant.
3. (Skip rotation in 5h — steps 1–2 suffice.)
For held gestures, capture the vector at the **gesture-hold frame** (hand velocity below threshold). **Average the last 3 held frames** before storing/comparing to beat jitter.

**Recognition — two-tier:**
```
1. BASE:     generic k-NN classifier -> (token, conf_base)
2. PERSONAL: 1-NN vs this user's prototypes in normalized space -> (token, dist)
3. FUSE:     if user has prototypes for the token AND dist < TAU (loose: 0.20),
             personal match WINS; else fall back to base.
```

**Confidence gating (when it learns):**
```
conf >= 0.85          -> ACCEPT silently -> speak it
0.55 <= conf < 0.85   -> show TOP-3 -> user taps the right one -> STORE prototype (LEARN)
conf < 0.55           -> "Sign that again?" -> capture -> user labels -> STORE (LEARN)
```
Every correction appends one normalized vector to `prototypes[token]`.

**What's REAL vs THEATER (be honest):**
- **REAL & the beat:** enrollment = a **class-addition**. "Teach a sign" → capture 3 held frames → **new chip provably appears in the Sign Profile**, counter ticks. This *cannot* fail like neural training — it is the guaranteed visual the words land on.
- **BONUS (can miss live):** the *next-sign re-recognition* firing. Backed by staged-input hotkey if it misses. **Rehearse so the chip appearing is the beat, not the re-fire.**
- **CUT as load-bearing:** the live-climbing accuracy curve (theater — at most a static decorative sparkline). Say *"watch it learn a sign I invented,"* never *"watch it get more accurate."*
- **Language:** "learns," "adapts," "remembers your signing." **Never** "trains" or "fine-tunes."

**Live demo metric (the honest curve):** decouple **"it entered my vocabulary" (unfailable)** from **"it fired on the next sign" (bonus)**. The vocabulary gain is the guaranteed beat.

### SUPPORT — Cekura Hearing-Side Hardening (pre-baked)
Real failure modes: *"Is this a robocall?"* → instant hangup; impatient IVR; long hold; *"I can only speak to the patient."* (The NAD "Don't Hang Up" campaign exists for exactly this.)
**Mechanism:** Cekura simulates adversarial personas → scores each call (completed? hung up?) → failures edit the agent's **opener / self-identification / persistence config** (prompt + few-shot, **not** weights) → re-run → completion rate climbs.
**Honest 5h scope:** run it **beforehand** to produce **v0 naive → v1 hardened** with real before/after scores → a **pre-computed card**. ONE live element: a single adversarial call where the hardened opener survives *"is this a robocall?"* **Past tense on stage:** *"We ran N adversarial calls through Cekura beforehand — here's before and after."* Never imply the curve moved live.

### One-line judge framing
> *"Two feedback loops. The agent learns the **Deaf user's** signing on-device with every correction, and learns the **hearing world's** hostility through Cekura. Eval data from both flows straight back in — one makes it understand you better, the other makes it impossible to hang up on."*

---

## 8. Sponsor Map (load-bearing role + win-the-prize move)

- **NVIDIA — Nemotron LLM + Nemotron Speech ASR (the brain + the ear).** The conducting agent: expands signed *intent* into natural speech and transcribes the hearing party. **Win move:** run the entire live path on **open NVIDIA models only** (no OpenAI/Anthropic/Google in the live path) and make a beat be Nemotron *reasoning about intent* (`APPOINTMENT` → *"Hi, I'd like to book an appointment"* + handles the follow-up). Say *"end-to-end on open NVIDIA models."* Endpoint: OpenAI-compatible ALB, model `nvidia/nemotron-3-super`, **`chat_template_kwargs.enable_thinking=false`** (mandatory — else `content` is null). ASR: `ws://44.241.251.184:8080`.
- **Pipecat — orchestration (the spine).** `on_client_message` (sign tokens) → `TTSSpeakFrame` onto Twilio → ASR back → captions to client. **Win move:** "used exactly as designed — frames, transports, client messages — to do something it was never demoed doing: drive a live call from sign language." Fork `pipecat-ai/yc-voice-agents-hackathon`.
- **Twilio — telephony (the real call).** A genuine two-way PSTN call to a real human. **Win move:** *"A real phone number rang. The Deaf user placed a real call. That's product, not a prompt."* Twilio Media Streams ↔ Pipecat transport.
- **Cekura — sim/eval/red-team (the proof).** Pre-demo hardening + the before/after card + one live adversarial-call survival. **Win move:** show the **before/after hardening** (past tense) — Cekura's whole thesis is "did you actually make it reliable." Highest-signal move for their prize.
- **AWS — hosting (honest: thin → made deliberate).** Co-locate the **entire runtime** (Pipecat bot + static sign client) in **us-west-2** next to the NVIDIA endpoints → *"single-region, sub-second sign-to-speech."* S3/CloudFront for the recorded backup. **Win move (honest):** *"We co-located the whole real-time pipeline next to the NVIDIA endpoints to hold sub-second round-trips."* Don't oversell — lead with NVIDIA + Cekura.

---

## 9. UI/UX Spec — "Signal Room"

**Aesthetic:** air-traffic-control meets ElevenLabs studio — calm, technical, confident, **dark**. NOT consumer-cute, NOT clinical, NOT AI-slop. No purple gradient, no Inter-on-white, no card-stack-on-lavender.

**Color:**
- Base `#0A0C10` · panel `#12151C` · hairline `#1E2430`.
- **"Live Signal" cyan-green `#3DF5C5`** — ONLY for active recognition + the speaking waveform (scarcity = premium).
- **Hearing-party amber `#F5B23D`** — captions from Aarya. *Two directions, color-coded: YOU = cyan, THEM = amber.* (Single best UX decision — direction is never ambiguous.)
- Text `#E8EDF2` / secondary `#8A94A6` · error `#FF5C5C`.
- Landmark overlay: connections `#3DF5C5` @70%, joints `#FFFFFF` 2px dots.

**Type:**
- **Display/captions:** `Geist` or `Space Grotesk` — captions are the hero: **56–72px**, tracking `-0.02em`, weight 600.
- **Mono/HUD/telemetry:** `Geist Mono` or `JetBrains Mono` — latency, sign-profile list, eval card. The mono reads "engineered," not "AI app." **Never Inter.**

**Layout (16:9, three zones):**
```
┌───────────────────────────────────────────────────────────────────┐
│  ◖ SIGNAL ROOM        ● LIVE CALL · Aarya · 00:42   RECOG 220ms ▮  │  top bar: call state + REAL latency HUD + speaking waveform
├──────────────────────────────────┬────────────────────────────────┤
│   [ CAMERA + LANDMARK OVERLAY ]  │  SIGN PROFILE          11 signs │
│   (60% width, mirrored/selfie)   │  ✓ HELLO   ✓ APPOINTMENT        │
│                                  │  ✓ THANK-YOU ✓ CANCEL           │
│   recognizing ▸ "APPOINTMENT"    │  ✓ YES ✓ NO ✓ WAIT ✓ REPEAT     │
│   ▁▂▅█ confidence 0.94            │  + TEACH A SIGN                │
│                                  │  ───────────────────────────── │
│                                  │  accuracy ▁▂▃▄▅▆ (decorative)  │
├──────────────────────────────────┴────────────────────────────────┤
│  YOU   →  "Hi, I'd like to book an appointment for Thursday." cyan │  caption rail (both directions)
│  AARYA →  "Sure! What time works for you?"                   amber │
└───────────────────────────────────────────────────────────────────┘
```
- **Camera:** large, panelled (not full-bleed), 1px cyan inner glow when a sign is actively recognized. **Mirror the feed** so signing feels natural.
- **Caption rail:** the emotional center — each utterance slides up with a spring, color-coded by speaker, old lines dim to `#8A94A6`. **Huge font** — readable from the back row.
- **Sign Profile:** top-to-bottom; the empty **"+ TEACH A SIGN"** slot is the affordance for the live enrollment beat.

**Key animations (framer-motion):**
1. **"Recognized" pulse** — on threshold cross, camera border does a 200ms cyan glow-pulse; token snaps in `scale 0.9→1, opacity 0→1`, spring `stiffness 400 / damping 28`. Instant, not floaty.
2. **Speaking waveform** — top-bar cyan bars driven by **real TTS amplitude** whenever speech plays (the audience *sees* the phone being spoken to). Stops crisply. **Do not fake the envelope** — drive from the audio or omit.
3. **Caption slide-up** — new line from `y:16, opacity:0` → settles; previous dims; staggered by speaker color.
4. **"Learned a new sign" (hero animation)** — new chip materializes with a cyan sweep, counter rolls `11→12`, toast *"WATER added to your vocabulary."* Next time it's signed, the chip flashes. 1.2s, satisfying, earned.
5. **Latency HUD** — the ms number is a **real measured `performance.now()` delta** with a thin sparkline. **Never a frozen or fabricated number** (a latency-themed demo dies on a faked headline number).

**Accessibility (this is an ASL product — non-negotiable):** everything critical is **visual + text**, zero reliance on sound for the Deaf user; captions ≥56px, AAA contrast, speaker-labeled, color-coded; no flashing >3Hz; generous timing.

---

## 10. The ~90s Demo Script (beat by beat)

**Cast:** Arav = Deaf user, signs to laptop camera. Aarya = hearing party, holds a real phone (visible), plays "front desk."

**Pre-stage (the app-must-open rule):**
- App already **open and warm** — camera live, landmarks tracking idle hands. **No live `npm run dev` on stage.**
- **Dial at T-minus ~15s** (NOT pre-pitch — an open PSTN call goes stale/times out). Aarya answers on the first ring. The real ring is a feature — the audience *hears* a real call.
- **Staged-input armed:** keys `1–8` fire the exact intended sign frames if MediaPipe misreads under stage light. You sign *and* press — belt and suspenders.
- **Recorded backup** queued full-screen, one keystroke away. If anything smells wrong in the first 10s, cut to tape and narrate live.

| Time | Who | Action | On screen | Spoken/Signed |
|---|---|---|---|---|
| 0:00–0:10 | Arav | **Ethics + the wound (sentence #1).** | Signal Room idle | *"We're hearing builders — this ships only with Deaf leadership. Nothing about us without us. Today, every phone call a Deaf person makes has a stranger on it — a human interpreter listening in. Watch."* |
| 0:10–0:25 | Arav signs | **HELLO → APPOINTMENT** | tokens snap (cyan), conf 0.9+, **RECOG ~220ms** | Agent SPEAKS onto the call: *"Hi, I'd like to book an appointment."* — cyan waveform fires |
| 0:25–0:40 | Aarya (real phone) | Speaks back | amber caption slides up: *"Sure — what day works?"* | Audience hears Aarya's real voice + reads the caption |
| 0:40–0:55 | Arav signs | **THURSDAY** (fingerspell) **→ THANK-YOU** | tokens + caption | Agent: *"Thursday works great, thank you."* Aarya: *"Booked for Thursday at 2."* |
| 0:55–1:15 | **Self-improvement** | *"It doesn't know my sign for WATER yet."* Taps **+ TEACH A SIGN**, signs WATER 3×. | **"WATER added"** toast, counter **11→12**, chip sweeps in | *"I just taught it a sign I use — in ten seconds. No retraining, no engineer."* Then signs WATER → agent speaks it; chip flashes. |
| 1:15–1:25 | Cekura | Cut to the pre-baked card | Card: *"Cekura adversarial 'robocall?' persona — v0 hung up; v1 hardened survived. Completion 40% → 92%."* | *"We ran adversarial calls through Cekura beforehand — here's the agent before and after hardening."* |
| 1:25–1:30 | Close | Hang up; timer freezes | "00:48" | **"For the first time, this call had no human interpreter listening in."** |

**Wow line lands LAST** — only hits after the audience has watched a real two-way call happen with no interpreter.

**De-risk checklist (hard gates):**
- [ ] App auto-opens to warm state via saved URL/local server. No live dev server on stage.
- [ ] Camera permission pre-granted on the exact demo laptop; tested under harsh/venue-like light.
- [ ] **Tether to a 5G phone hotspot, NOT venue WiFi** (congested/NAT'd WebSocket = silent killer). Pre-flight the exact path.
- [ ] Twilio dialed at T-15s. Aarya's phone **off-silent, screen-awake, max volume, known-good cell/landline** (not stage VoIP). Backup number = Arav's second phone, ringer on.
- [ ] Latency HUD labeled **"recognition"**, measured for real — so a cloud spike never contradicts the headline.
- [ ] Cekura card run earlier, hardcoded — **never run live.**
- [ ] **Full-loop screen+audio recording exists on the venue network = the go/no-go gate.** No recording, no go-live.
- [ ] Lighting locked: clip-on fill light + dark sleeves + dark background.
- [ ] Rehearse the full 90s **5×** before submission. The April-23 loss was an un-rehearsed open.

---

## 11. Hour-by-Hour Build Plan (~5h, 2 people, parallel)

**Owners:** **Arav = CLIENT** (browser, MediaPipe, recognition, enrollment, UI). **Aarya = BOT** (Pipecat, Twilio, Cartesia TTS, Nemotron ASR, captions). **The bridge is the integration risk — lock the message schema in the first 15 min.**

**Message schema (lock at T+0:15, both build against it):**
```
client -> bot:  { type: "sign", token: "APPOINTMENT", mode: "verbatim" | "conduct" }
bot -> client:  { type: "caption", speaker: "aarya", text: "...", ts }
bot -> client:  { type: "spoken",  text: "...", ts }   // for the YOU caption + waveform
```

| Time | Arav (CLIENT) | Aarya (BOT) | Joint gate |
|---|---|---|---|
| **H0 · 0:00–0:30 — SMOKE TEST (app must open)** | Fork starter; get MediaPipe Hands rendering landmarks in-browser. **Test recognition under HARSH light in first 30 min** — if 1-NN jitter is bad, fix normalization NOW before anything else. | Fork `pipecat-ai/yc-voice-agents-hackathon`; place a real Twilio call to Aarya's phone; confirm bot ↔ Twilio audio works. | **Both apps open and run. Lock the message schema.** |
| **H1 · 0:30–1:30 — THE BRIDGE (riskiest)** | Build a `<button>SPEAK "Hi, I'd like to book an appointment"</button>` that fires the **exact** `sendClientMessage` path. | `on_client_message` → `TTSSpeakFrame(text, append_to_context=False)` → spoken onto the call. **Test verbatim AND conduct paths in isolation** (kill the double-speak bug). | **Button → Aarya's ear works. THE feature exists.** Record a 30s proof now. |
| **H2 · 1:30–2:30 — RECOGNITION → SPEAK** | Wire k-NN (A–Z + 8 commands) over normalized landmarks; dwell-commit (150–250ms); confidence gate; gesture → fixed string → bridge. Real `performance.now()` latency HUD. | Nemotron `LLMService` wired (`enable_thinking=false`) for the conduct beat; verify `content` non-null. Cartesia TTS swapped in. | **A signed gesture → spoken on the call.** |
| **H3 · 2:30–3:30 — TWO-WAY + ENROLLMENT** | Build **"Teach a sign"**: capture 3 held frames → normalize → append prototype → **chip appears** + counter ticks (the guaranteed beat). Sign Profile panel. | Nemotron ASR (`ws://44.241.251.184:8080`) on inbound audio → `server→client` caption messages. | **Aarya's reply → big caption. Enrollment chip appears.** *Decision point: if bridge/conduct unproven, lock to verbatim, cut Nemotron expansion.* |
| **H4 · 3:30–4:15 — POLISH + CEKURA** | Signal Room styling (dark, cyan/amber, Geist/Geist Mono), caption rail spring, recognized-pulse, learned-sign animation, speaking waveform from real TTS amplitude. | Run **Cekura before/after** suite → screenshot the v0→v1 card. Wire the ONE live adversarial-call fallback. Co-locate runtime in us-west-2. | **Demo looks like Signal Room. Cekura card ready.** |
| **H5 · 4:15–5:00 — RECORDED BACKUP + REHEARSE** | **Record the full 90s loop ON THE VENUE NETWORK the instant it works (hard go/no-go gate).** Stage staged-input hotkeys `1–8`. | Pre-dial timing rehearsal; Aarya's phone settings locked; backup number ready. | **Backup recorded. Rehearse the 90s ×5. Submit.** |

**The ONE feature that must work:** committed sign → spoken onto the real Twilio call to Aarya. Everything after H2 is additive; everything in H4 is garnish — cut on any slip.

---

## 12. Risk Register (top 5) + Mitigations

| # | Risk | Sev | Mitigation |
|---|---|---|---|
| 1 | **Browser↔bot↔live-call bridge dies on stage** (two failure surfaces only exist combined). | CRITICAL | Lock schema at T+0:15; prove with a `<button>` before wiring gestures; record a proof at H1; full-loop recorded backup is the go/no-go gate. |
| 2 | **`append_to_context` double-speak** — agent talks over itself onto the call. | HIGH | One path per utterance: hero = fixed string, `append_to_context=False`, no LLM; conduct = Nemotron sole producer. Test both in isolation in H1. |
| 3 | **MediaPipe fails under stage lighting** → garbage spoken / no recognition. | HIGH | Clip-on fill light + dark sleeves + dark background; test under harsh light in first 30 min; confidence gate; staged-input hotkeys `1–8`; fixed phrase allowlist. |
| 4 | **Venue WiFi kills WebSocket/Twilio media** (congested, NAT'd). | HIGH | Tether to 5G hotspot (not venue WiFi); pre-flight the exact path; dial Twilio at T-15s; Aarya's phone off-silent/known-good line; backup = Arav's second phone. |
| 5 | **Ethical misread — appropriation / faked numbers.** | MED-HIGH | Open with "nothing about us without us"; sign cleanly + minimally; cite real Deaf-user input; lead privacy not disability; **measure the latency number for real**, label honestly ("no human interpreter," not "only two people"). |

---

## 13. Post-Hackathon One-Liner

**Launch tweet:**
> A Deaf person signs to their phone — and it makes the call. Real two-way phone call, real hearing party, **no human interpreter listening in.** ASL in, the agent *conducts* the call, replies come back as live captions. On-device sign recognition. Built on open NVIDIA models. Nothing about us without us — Deaf-led from here. 🤟📞

**Keep-URL-live:** ship the warm Signal Room demo to a stable URL (Vercel front-end + Pipecat bot in AWS us-west-2; recorded backup on S3/CloudFront). One link, always loads to the warm state, recorded loop embedded as fallback — so anyone who clicks sees the empty third chair, live or on tape.

---

*Locked. Build the real two-way call + the honest 10-second sign-enrollment. Cut everything that can fail in front of it. The win is the empty third chair — protect it.*