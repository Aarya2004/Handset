Looking at five design briefs that are remarkably aligned. My job is to break them. Let me stress-test against the two killer risks plus the failure modes, and surface where they're lying to themselves.

I have everything I need in the briefs — no tool calls required. Here's the adversarial pass.

---

# RED-TEAM VERDICT: ASL Phone Agent

The five briefs are unusually coherent and mostly honest — which is itself a risk: **internal consensus is not external validation.** They've all converged on the same story, so they share the same blind spots. Below are the issues they collectively missed or under-weighted.

---

## KILLER RISK 1 — LATENCY HONESTY

**The briefs are 90% honest here. The remaining 10% is where you get killed live.**

### ISSUE L1 — The "118ms" number is a landmine even when honestly labeled. [SEVERITY: HIGH]
Every brief leans on a two-number split: "118ms recognition (true)" + "~0.9s to Aarya (honest)." Good instinct. But there are **three** dishonesty traps the briefs don't all close:

1. **118ms is recognition latency, NOT sign-to-text latency.** Your own self-improvement brief mandates a **200–400ms dwell/debounce** to commit a sign. So the *user-perceived* "I finished my sign → it appeared" time is **dwell + inference = 300–500ms, not 118ms.** The 118ms is per-frame inference, which the user never experiences in isolation. If you flash "118ms" while the audience watches a visibly longer commit, an observant judge clocks the mismatch. **The MVP brief got this right (label it "sign recognition latency"); the latency brief is internally inconsistent — it both says "commit dominates the budget at 150–400ms" AND wants to flash "RECOGNITION: 112ms."** Pick one definition. You cannot show 112ms and also have a 250ms dwell.

   **FIX:** The HUD number must be the number the audience can verify with their own eyes: **time from sign-commit to on-screen token.** That's ~150–250ms with a tight dwell. Show *that*, call it "recognition," and it survives scrutiny. Showing per-frame 112ms is the kind of technically-true/experientially-false claim that reads as a lie when caught. **Round honest: "under 250ms to recognize."**

2. **The "micro-jittering HUD" (MVP brief animation #5) is fabricated telemetry.** A latency number that jitters "like real telemetry" when it is NOT measuring real round-trips is *staged data presented as live measurement.* If a judge asks "is that real-time?" and it's a synthetic envelope, you've crossed from honest-framing into fraud. Same problem with the "believable synthetic envelope" for the speaking waveform.

   **FIX:** Either measure it for real (trivial — `performance.now()` deltas around the commit event; you already have the events) or label it as a fixed spec number, not a live readout. **Real measurement is ~20 min of work. Do it. Never fake a number on a latency-themed demo.**

3. **Nobody timestamped the ASR return leg.** Aarya speaks → Nemotron ASR → caption. That's another **300–800ms** (ASR is streaming but not instant, plus the inbound PSTN leg). The briefs obsess over the outbound budget and hand-wave the return. On stage, the gap between Aarya's mouth moving and the amber caption appearing is **visible and unflattering** if it's >1s. None of the five briefs put a number on it.

   **FIX:** Budget it honestly (~0.5–1.0s caption lag) and *use the lag as narrative*: the caption appears, Arav reads, then responds — the rhythm sells "real conversation," not "instant magic." But rehearse it; if ASR lags 2s the demo feels broken.

### ISSUE L2 — "Faster than a human interpreter" is the load-bearing claim and it's under-defended. [SEVERITY: MEDIUM]
The entire honest-framing rests on "~0.9s beats a human VRS relay's 2–4s." **Is that 2–4s number sourced?** The briefs assert it without citation. A judge who has used VRS (or a Deaf judge) may say "my interpreter is faster than that." If your baseline is wrong, your one impressive comparison collapses.

**FIX:** Soften to a claim you can defend without a stopwatch: *"comparable to a live conversation, and there's no third person on the line."* Lead with **autonomy/privacy** (unimpeachable) and treat speed as secondary. Don't stake the pitch on a relay-latency number you can't prove on stage.

---

## KILLER RISK 2 — SELF-IMPROVEMENT REALNESS

**Here the briefs openly disagree with each other, and the disagreement is the most important finding in this entire review.**

### ISSUE S1 — The self-improvement brief and the MVP brief contradict on what's real. [SEVERITY: CRITICAL]
- **Self-improvement brief:** "It learned my sign" via 1-NN + correction. Claims the post-correction confidence jump is "deterministic, not luck." Admits "MILD THEATER: seed the accuracy curve."
- **MVP brief:** Explicitly calls the live-learning *moment* a **TRAP**, says "keep the moment, fake the mechanism honestly," and bans the climbing accuracy curve as load-bearing proof.

**These are not the same plan.** One makes the learning loop the STAR (2.5 of 5 hours). The other says the learning loop is the highest-variance thing on stage and demotes it to ambient telemetry. **You cannot build both. This must be resolved BEFORE anyone writes code, or you'll burn 2 hours building a star the other half of the team thinks is a liability.**

**My adjudication (siding ~70% with the MVP brief):**
- The **1-NN enrollment mechanism is genuinely real and genuinely safe** — adding a template class to a k-NN matcher cannot fail like neural fine-tuning. The self-improvement brief is correct that the *mechanism* is honest and buildable in 5h. ✅
- BUT the self-improvement brief's **"deterministic confidence jump"** claim is **overstated and fragile.** 1-NN distance to a stored prototype is near-zero *only if MediaPipe landmark jitter is low and the user reproduces the handshape closely.* On stage, under different lighting, with adrenaline, Arav's re-signing of WATER may land at cosine distance 0.18 when TAU is 0.15 → **it doesn't fire, and the "it learned me" moment dies live.** The brief's own mitigation (loosen TAU to 0.2, average 3 frames) is right but undersold — and loosening TAU raises false-positive risk on *other* signs.
- The **"accuracy curve climbing live" is theater** and the MVP brief is right to kill it as load-bearing. The self-improvement brief admits seeding it — a seeded curve that "climbs" on stage is exactly the kind of thing that reads as rigged if anyone looks closely.

**HONEST MINIMAL VERSION THAT ACTUALLY WORKS ON STAGE (build this):**
1. **Enrollment is the proof, not the curve.** "Teach a sign" → capture 3 held frames → new chip appears in Sign Profile → it fires on the very next sign. This is real, visible, and unfailable *as a class-addition* (the chip provably appears). 
2. **Decouple "it appeared in my vocabulary" (unfailable) from "it fired correctly on the next sign" (can miss).** The *vocabulary gain* is the guaranteed visual. The *next-sign firing* is the bonus. If firing misses live, you still have the chip + you have staged-input hotkey to force it (MVP brief's mitigation). **Rehearse so the chip appearing is the beat the words land on, not the re-recognition.**
3. **Kill the live accuracy curve as a hero element.** Demote to a static "ambient" sparkline that is clearly decorative, or cut it. Do not say "watch it get more accurate" — say "watch it learn a sign I invented." The former is theater; the latter is a true class-addition.
4. **Pre-test the confidence jump in the first 30 min** (self-improvement brief says this — non-negotiable). If 1-NN is jittery under venue light, you find out before you've bet the demo on it.

**Net on Risk 2:** Not pure theater — the enrollment is real. But the briefs over-promise on "deterministic" re-recognition and the "climbing curve." The honest minimal version is **"I taught it a new sign and it entered my vocabulary live"** — that is true, safe, and emotionally sufficient. Drop everything beyond it.

### ISSUE S2 — Cekura "self-improvement curve" is pre-baked but pitched ambiguously. [SEVERITY: MEDIUM]
The sponsor + self-improvement briefs are honest that the Cekura curve is **pre-computed (v0→v1 config), not live retraining.** Good. But the demo script (MVP brief) shows a "score 9.1/10" card with no temporal framing, and the sponsor brief wants to "show the self-improvement curve live." If you flash a climbing curve and imply it happened during the demo, that's dishonest.

**FIX:** Say the exact words: *"We ran N adversarial calls through Cekura beforehand — here's the agent before and after hardening."* Past tense. The ONE live element is a single adversarial call surviving "is this a robocall?" — which is real. Never imply the curve moved on stage.

---

## LIVE-DEMO FAILURE MODES (what the briefs under-weighted)

### ISSUE D1 — Stage lighting on MediaPipe is named but not mitigated with a real plan. [SEVERITY: HIGH]
Every brief says "stage lighting might break MediaPipe" and every brief's mitigation is "staged-input hotkeys 1–8." **That's a fallback, not a mitigation — it means you've conceded recognition may not work live and you're keypressing the demo.** Which is fine as insurance, but if recognition visibly fails and you're obviously hammering number keys, the "118ms recognition" headline is contradicted in real time.

**FIXES (additive, do all three):**
- **Control your own lighting.** Bring a small clip-on LED / ring light for Arav's hands. Stage uplighting from below wrecks hand landmarks; a front fill light fixes 80% of it. ~$20, decisive.
- **Plain dark background behind the hands** (wear long dark sleeves; MediaPipe segments hands better against contrast). The MVP brief's own dark aesthetic helps here — lean into it.
- **Rehearse ON the venue stage during setup if at all possible**, or at minimum under bright/harsh light at the hackathon space. The self-improvement brief's "test in first 30 min" must be *under demo-like light*, not office light.

### ISSUE D2 — Pre-dialed Twilio call cannot be held open for the whole pitch. [SEVERITY: HIGH]
Multiple briefs say "pre-dial the call and keep it warm." **Problem:** an open PSTN call with dead air for 2–3 minutes while you do your intro will often (a) hit carrier silence-timeout, (b) trigger Aarya's phone screen-lock/audio-routing change, or (c) Twilio may emit periodic events. A call connected at 0:00 and first-spoken-to at 0:15 might already be degraded.

**FIXES:**
- **Dial at T-minus ~15s**, not before the pitch. Have Aarya answer on the first ring (she's primed). One keystroke dials. Practice the cold-dial timing — it's ~3–5s of ring, budget it into the script (it actually *helps* — the audience hears a real phone ring, which sells "real call").
- **Aarya keeps the phone OFF silent, screen-awake, max volume, on a known-good cell or landline** — not stage WiFi VoIP.
- **Backup number = Arav's own second phone** in his pocket, ringer on, so if Aarya's line fails he redials a guaranteed-live number and narrates.

### ISSUE D3 — Venue network is the silent killer and no brief has a hard plan. [SEVERITY: HIGH]
Pipecat bot ↔ Twilio media streams ↔ AWS us-west-2 ↔ browser client all over **hackathon WiFi**, which is congested, NAT'd, and may block WebSocket/UDP. The sponsor brief's "co-locate in us-west-2" reduces server-server RTT but does **nothing** for the venue-WiFi-to-AWS hop, which is the leg that actually dies.

**FIXES:**
- **Tether to a phone hotspot (LTE/5G), not venue WiFi**, for the demo laptop. Test it. A clean 5G hotspot beats congested venue WiFi for WebSocket stability every time.
- **Pre-flight the exact path on the venue network the morning of** and record the backup *on that network* the moment it works (every brief says this — make it a hard gate: no recording = no go-live).
- **Recorded backup must be a real screen+audio capture of the actual working loop**, full-screen, one keystroke to play, with the laptop's live app behind it. If anything smells wrong in the first 10s, cut to tape and narrate. This is the April-23 insurance and it's correctly mandated — escalate it from "should" to "the demo does not start until this file exists."

### ISSUE D4 — `append_to_context=true` + LLM-in-loop double-speak. [SEVERITY: MEDIUM]
The latency and sponsor briefs *conflict*: latency brief says **bypass the LLM** for the hero moment (pure TTS injection); sponsor + MVP briefs want **Nemotron expanding intent → full sentence** as the NVIDIA wow ("CALL_PHARMACY + R-E-F-I-L-L" → polite sentence). With `append_to_context=true`, an injected TTSSpeakFrame *plus* an active LLM context can cause the LLM to also generate a response → **the agent talks over itself or double-speaks onto the live call.**

**This is a real, specific, demo-killing bug and it's the most concrete technical risk in all five briefs.**

**FIX (resolve before building):** Pick ONE path per utterance.
- **Hero verbatim beat:** intent → fixed string → `TTSSpeakFrame` with `append_to_context=FALSE` (don't pollute context), LLM not invoked. Deterministic, no double-speak.
- **NVIDIA "it conducts" beat:** intent token → Nemotron generates the sentence → that single generated string is spoken. The LLM is the *producer* of the utterance, not a parallel responder. Make sure the pipeline doesn't ALSO auto-respond to the user-turn. **Test both paths in isolation early** (latency brief's "prove with a button first" applies here).

---

## ETHICAL LANDMINES (the briefs are good here — two gaps remain)

### ISSUE E1 — A hearing team signing on stage is itself the risk the briefs warn about. [SEVERITY: MEDIUM-HIGH]
The novelty brief brilliantly lists the words to avoid — then the *entire demo* is **Arav (hearing) signing ASL on stage.** The brief itself flags "no hearing person signing badly as a punchline." But the hero moment *requires* a hearing person signing, possibly badly, in front of Deaf-adjacent judges. This is the single most likely thing to read as appropriation.

**FIXES:**
- **Name it before they do.** Open with: *"We're hearing builders — this ships only with Deaf leadership. Nothing about us without us."* The novelty brief has the exact words; make them the FIRST sentence, not a footnote at 1:25.
- **Sign cleanly and minimally.** Fingerspelling A-Z + a tiny command set, rehearsed to look competent, not flailing. Sloppy signing is the appropriation tell.
- **If at all possible, get a Deaf person's input before the demo** (even 10 min async) and *say you did*. "We showed this to a Deaf ASL user and they said X" is worth more than any latency number to this audience.

### ISSUE E2 — "The empty third chair" is a beautiful line that slightly overclaims. [SEVERITY: LOW-MEDIUM]
"For the first time this call had only two people in it" — except there's a cloud LLM, an ASR service, Twilio, and AWS all "on" the call. The privacy claim ("no human listening") is true and powerful; the "only two people" framing invites a clever judge to say "your LLM logged every word." For a Deaf community sensitive to surveillance, this matters.

**FIX:** Tighten to the defensible claim: *"No human interpreter listening to your private call."* Add one line about on-device sign processing (MediaPipe is local — true!) and a roadmap commitment to no-retention/on-device LLM. Don't claim "only two people" when there's a cloud pipeline; claim "no human eavesdropper," which is what people actually care about.

---

## IS THE MVP STILL TOO BIG FOR 5h / 2 PEOPLE? — YES, MARGINALLY. [SEVERITY: HIGH]

The MVP brief's own "IN" table has **7 features**. The self-improvement brief allocates 2.5h to the learning loop alone. The sponsor brief wants Nemotron intent-expansion AND ASR return AND Cekura AND AWS co-location. **Two people cannot build all of this to "won't-fail-live" polish in 5 hours.** The briefs each individually scope well but *collectively* re-inflate the scope — classic multi-brief creep.

**The honest critical path (everything else is optional/cut):**
1. **Browser MediaPipe → committed sign → `sendClientMessage` → `TTSSpeakFrame` → Twilio call → Aarya hears it.** (THE feature. If only this works, you have a demo.)
2. **Aarya's reply → ASR → caption back.** (Makes it two-way — the real wow. Second priority.)
3. **Enrollment "teach a sign" → chip appears.** (The honest self-improvement beat. Third.)
4. Everything else — Nemotron intent-expansion, Cekura live, AWS co-location, accuracy curve, react-three-fiber — is **garnish, cut on any time pressure.**

**Parallelize across 2 people:** One owns the browser/MediaPipe/recognition/enrollment client. One owns the Pipecat bot/Twilio/TTS/ASR/captions. The **bridge between them (`sendClientMessage` contract) is the integration risk** — define the message schema in the first 15 minutes so both can build against it independently, and prove it with the button-test (latency brief) before lunch.

**Hard cut now:** Cekura live-call beat (keep only the pre-baked card), AWS co-location (keep only "hosted on AWS" as a sentence), the accuracy curve (cut entirely or static decoration), any 3D/particle field, Nemotron intent-expansion *if the bridge isn't proven by the 3h mark* (fall back to verbatim fixed strings).

---

## MUST-FIX BEFORE BUILDING (prioritized)

1. **[CRITICAL] Resolve the self-improvement contradiction.** Self-improvement brief (star, 2.5h) vs MVP brief (trap, demote to ambient). **Decision: enrollment = real and is the beat; "climbing accuracy curve" = cut; re-recognition firing = bonus, backed by hotkey.** Agree this in writing before code.
2. **[CRITICAL] Resolve `append_to_context` double-speak.** One path per utterance. Hero = verbatim, `append_to_context=False`, no LLM. Test both paths in isolation in the first hour.
3. **[HIGH] Fix the latency number.** HUD shows *sign-commit-to-on-screen* (real, ~150–250ms, measured with `performance.now()`), labeled "recognition." Kill the fake jittering telemetry and synthetic waveform-as-data. Measure or label-as-spec — never fabricate.
4. **[HIGH] Define the browser↔bot message schema in the first 15 min** and prove the bridge with a `<button>SPEAK</button>` test before wiring gestures. This is the single riskiest integration.
5. **[HIGH] Lock the lighting + background plan** (clip light, dark sleeves, dark bg) and test recognition *under harsh light* in the first 30 min — before betting the demo on it.
6. **[HIGH] Network: tether to 5G hotspot, not venue WiFi.** Dial Twilio at T-15s, not pre-pitch. Aarya's phone off-silent, screen-awake, known-good line, backup = Arav's second phone.
7. **[HIGH] Recorded backup is a hard gate:** no full-loop recording on the venue network = demo does not go live. Record the instant it works once.
8. **[MEDIUM] Open with the ethics line** ("hearing builders, Deaf leadership, nothing about us without us") as sentence #1. Get even 10 min of real Deaf input and cite it.
9. **[MEDIUM] Soften the over-claims:** "no human interpreter listening" (not "only two people"); "comparable to a live conversation" (not an unsourced "faster than 2-4s VRS").
10. **[MEDIUM] Cut to critical path:** features 1-3 only. Cekura→pre-baked card. AWS→one sentence. No 3D, no live curve. Parallelize: one on client, one on bot.

---

## FINAL VERDICT: **GO-IF**

The concept is sound (8.7 novelty holds), the architecture is correct, and four of the five briefs are refreshingly honest. **GO conditional on the 10 must-fixes above, and specifically on these three non-negotiables:**

- **GO-IF #1:** The team resolves the self-improvement star-vs-trap contradiction (MUST-FIX 1) and the `append_to_context` double-speak (MUST-FIX 2) *before writing code* — these are the two issues that will silently waste hours or kill the demo live.
- **GO-IF #2:** The latency HUD shows a real, eye-verifiable, measured number — no fabricated telemetry on a latency-themed demo (MUST-FIX 3). Faking the headline number on a demo whose whole pitch is honesty is the one thing that turns a win into a disqualifier.
- **GO-IF #3:** A recorded backup on the venue network exists before going live, and the ethics framing leads (MUST-FIX 7, 8).

If those three are met, this wins its track. If the team tries to build all 7 MVP features, ships a fake jittering latency number, and bets the demo on a live-climbing accuracy curve under stage lighting — **NO-GO, it fails live like April 23.** The difference is entirely discipline, not capability.

**The empty-third-chair is the win. Protect it by cutting everything that can fail in front of it.**