# Handset — Progress & Decisions

**Repo:** https://github.com/Aarya2004/Handset.git
**What it is:** A phone "handset" for people who can't speak into one. A Deaf/HoH person **signs at their webcam → the bot recognizes ASL → speaks on a phone call** to a hearing person (e.g. ordering from the Field & Flower flower shop). Built on the Pipecat hackathon starter.

**Time budget:** ~6h total (as of ~14:00, 2026-05-30). Treat every decision through "does this survive the clock?"

---

## Confirmed decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **MVP direction = ASL-IN** (sign → speech → phone). ASL-OUT (rendering signs back to the user) is a **stretch goal**, not MVP. | User's product vision. The name "Handset" = phone handset for someone who can't speak. |
| D2 | **Camera input over WebRTC** is required (frames from webcam into the Pipecat pipeline). | No way around it for ASL-IN. |
| D3 | Build a **custom camera client UI** (`enableCam:true`). The bundled prebuilt UI is **voice-only / screen-share only** — it can't open the Mac camera. | Verified live: only "share screen" offered, no `📹` frames ever arrived. |
| D4 | **Server-side `video_in_enabled=True`** + a `VideoFrameProbe` diagnostic processor. ✅ DONE, committed (`4fab3cb`), pushed to `handset/main`. | First milestone: prove frames reach the pipeline. |
| D5 | **Evals via Cekura** are a first-class requirement (judges weight this heavily). | README + hackathon framing. |
| D6 | **Frame transport = Path B: capture clip + POST.** Browser records webcam between "start" and "Send", uploads sampled frames to a `/sign` endpoint → Omni/vision → text → inject as user turn. WebRTC video track NOT required for MVP. **Build the happy path first.** | Matches how Omni consumes video (discrete N-frame request); simplest 6h build. Supersedes the need to publish a WebRTC video track. |

> **Note:** D6 means D4's `video_in_enabled`/`VideoFrameProbe` work is no longer on the critical path (we're not streaming video over WebRTC). Keep it — harmless, and useful if we ever switch to Path A — but the MVP flow is browser-clip → HTTP POST, not WebRTC video frames.

### Topology (CONFIRMED)
```
  ARAV (Deaf/HoH)                    BOT (interpreter)              AARYA (hearing)
  signs at webcam  ──clip POST──▶  ASL→text→Nemotron→TTS  ──Twilio──▶  real phone
  reads captions ◀──screen text──  Nemotron ASR (caption) ◀──Twilio──  talks back (voice)
```
- **Arav** = the non-speaking signer, at the laptop/webcam.
- **Aarya** = the hearing person, on a **real phone**, hears Arav's signed words spoken by the bot, replies by voice.
- ~~G7: return path to Arav~~ ✅ **RESOLVED (D9): caption Aarya's phone audio back to Arav's screen via Nemotron ASR.** Closes the loop into a real two-way conversation. ASL-rendered reply = "maybe later", not now.

| D7 | **Phone leg = real Twilio.** Support BOTH directions; **prioritize OUTBOUND** (bot rings Aarya's phone via Twilio REST API). Inbound (Aarya dials a Twilio number, starter's documented path) as secondary. | User priority. NOTE: outbound is custom (not in starter) — higher risk; see caveat below. |
| D8 | **Build local, deploy once at end.** Iterate ASL→text→speech loop locally (fast). Deploy to Pipecat Cloud + wire Twilio near end for the real-phone demo. | Twilio can't reach localhost; avoid slow redeploy loop all day. |

> ⚠️ **CAVEAT on outbound (D7):** Outbound calling is the *harder* Twilio path and is **not** in the starter (the README only documents inbound via TwiML Bin). It also still requires the bot to be reachable by Twilio's media stream (cloud deploy). Inbound is lower-risk and gives the **same demo experience** ("I'm on a phone call hearing his signs"). Recommend: get **inbound working first** as the safety net, then attempt outbound as the preferred version if time allows. Flagged for Aarya to confirm.

## Open / in-progress

| # | Item | Owner | Status |
|---|------|-------|--------|
| O1 | **Get a Nemotron Omni (multimodal) endpoint** we can route to. If it works, it READS the ASL directly → no MediaPipe, no training. Huge risk-remover. | Aarya (30 min) | ⏳ trying |
| O2 | **Camera client UI** (vanilla-JS WebRTC page, mic+cam, POST offer to `/api/offer`). Needed regardless of which model reads frames. | Claude | 🔨 building |
| O3 | **Sign-recognition stage** — the actual sign→text. Depends on O1 outcome (Omni vs. fallback). | — | ⛔ blocked on O1 |
| O4 | **Cekura eval — BOTH surfaces** (D10). | — | 🧠 design ready |
| O5 | **Text-injection back door (D11)** — build EARLY, before recognizer. | Claude | 🔨 next |

---

## Key findings (verified, not assumed)

- ❌ **The provided NVIDIA LLM endpoint is TEXT-ONLY.** `GET /models` → only `nvidia/nemotron-3-super`. Sending an image returns `"nvidia/nemotron-3-super is not a multimodal model"` (HTTP 400). **No multimodal shortcut on the given infra** — unless Aarya finds an Omni endpoint (O1).
- ✅ **Nemotron 3 Nano Omni exists** (NVIDIA, Apr 2026): native text+image+**video**+audio, uses Conv3D "tubelet" embeddings that capture **motion between frames** — a near-perfect fit for sign language. *If reachable*, it collapses the whole recognition problem.
- ✅ **Camera client is feasible.** `@pipecat-ai/small-webrtc-transport` + `client-js` support `enableCam:true` / `<PipecatClientVideo>`. Server expects `POST /api/offer` with `{sdp,type,pc_id,restart_pc}` + `PATCH` for ICE.
- ⚠️ **Full-vocab ASL recognition is an unsolved research problem** (~61% top-1 on WLASL's 2000 words). Any "recognize arbitrary ASL" claim will fail live. Small curated vocab is the only reliable path if Omni doesn't pan out.
- ⚠️ **ASL ≠ English word order.** Real ASL has its own grammar; naive sign→English mistranslates.

---

## OPEN QUESTIONS being grilled (the "what have we missed" list)

These are the gaps. See live grilling below — answers get folded back here.

- G1 — **The phone leg doesn't exist yet.** "Speaks on a phone call" — is there a real Twilio outbound call in the demo, or is "the phone" just the bot's spoken audio? This is a whole separate integration.
- ~~G2 — Turn-taking with no voice.~~ ✅ **RESOLVED: a "send" button.** Signer presses Send (button / spacebar) to mark end-of-turn. The frames captured between presses = one signed turn = the "user utterance". Reliable, demos cleanly, and defines the frame-capture window. Natural end-of-turn detection (hands-down / "DONE" sign) is a stretch goal.
- G3 — **Latency budget.** Sign → recognize → LLM (with thinking tokens) → TTS → phone. Could be many seconds. Is that acceptable for a live phone conversation?
- ~~G4 — Cekura can't sign.~~ ✅ **RESOLVED: eval splits along the sign→text boundary.**
  - **Surface 1 (D10): phone conversation = Cekura-native.** Cekura plays the hearing caller, speaks to the bot's phone side, scores workflow completion / tool calls (catalog, order) / quality / latency. Driven via the text back door (D11).
  - **Surface 2 (D10): recognizer accuracy = offline.** Labeled clips → recognizer → compare to label. Score via script and/or push to Cekura as a custom metric ("recognized_text_matches_intended_sign").
  - **D11: text-injection back door — BUILD EARLY.** A mode where the bot accepts a typed/POSTed "user turn" as if from the recognizer. Unblocks ALL conversation development (no signing needed to test) AND is the hook Cekura drives. Highest-leverage item.
- ~~G5/G6 — demo script + fallback~~ ✅ **RESOLVED.**
  - **D12: Recognizer is a swappable `frames → text` stage.** Tiered fallback: **Omni** (if O1 lands) → **curated known clips/signs** (guaranteed happy path) behind the same interface. Same demo either way. (MediaPipe fingerspelling = optional middle tier, only if time.)
  - **D13: Parallel build.** Phone-loop track (Aarya/Arav: Twilio + deploy) and recognizer track (Claude) proceed simultaneously; merge via the `frames→text` contract + text back door.
  - **Demo script:** Arav signs a known phrase → recognizer emits text → Nemotron places the flower order → **Aarya's phone rings, hears the order spoken** → Aarya replies by voice → **caption appears on Arav's screen.** Full two-way loop.

---

## 🎯 LOCKED SCOPE (Rule 2)

**IRREDUCIBLE MVP (perfect & test this FIRST, before adding ANYTHING):**
> **Arav signs → bot recognizes → bot SPEAKS the flower order on a real phone call to Aarya. ONE direction.**

Perfected, fool-proof across all demo conditions (Rule 3), proven working (Rule 1). This single flow IS the WOW.

**POST-MVP (layer on ONLY after core is bulletproof, in order):**
1. **Improvement beat (HEADLINE): Cekura-measured latency tuning.** Tune Nemotron `enable_thinking`/sampling for phone responsiveness → prove before→after latency drop with Cekura. Hits BOTH judging signals; uniquely justified by "it's a live phone call." (Accuracy loop = secondary beat if time.)
2. Caption-back to Arav's screen (D9) → makes it two-way.
3. Second Cekura surface (recognizer accuracy, D10-S2).
4. Outbound Twilio (D7) — inbound is the safety net.

> Caption-back (D9), two-surface eval, outbound — all explicitly **deferred** past the one-way core. Not fluff, just *later*.

## THE PLAN (synthesized — build order)

**ONE-WAY MVP only. Each step is PROVEN working (Rule 1) before the next. Recognizer is the last swappable piece.**

Every step ends with "✅ PROVE:" — the concrete test that must pass before moving on.

1. **Text back door (D11)** — bot accepts a POSTed/typed "user turn" as if from the recognizer.
   ✅ PROVE: POST `"I want a dozen red roses delivered tomorrow"` → bot speaks a correct flower-shop response locally.
2. **Conversation loop solid (local)** — Nemotron Super + flower-shop tools (catalog, order) driven by back-door text → Gradium TTS. (Mostly exists in `bot-nemotron.py`.)
   ✅ PROVE: a full typed-turn order completes correctly (right bouquet, delivery captured, order placed) — re-run after step 1 still works.
3. **Camera client (D6)** — browser page: webcam preview + **Send** button → records clip between presses → POST to `/sign`.
   ✅ PROVE: pressing Send POSTs a real clip; server logs receipt with frame count. (Old: back-door text still works.)
4. **Recognizer stage (D12)** — pluggable `frames → text`, tiered: **Omni** (if O1) else **curated clips**. Wire its output into the SAME path the back door feeds.
   ✅ PROVE: a known signed clip → correct text → bot speaks correct order. (Old: typed back door + camera POST still work.)
5. **Real Twilio phone leg (D7, D8)** — deploy to Pipecat Cloud, wire **inbound first** (safety net), then outbound. The spoken order comes out of Aarya's actual phone.
   ✅ PROVE: Aarya on a real phone hears Arav's signed order spoken. (Old: full local loop still works.)

→ **At this point the IRREDUCIBLE MVP is done and proven.** Only now: latency-tuning improvement beat, then caption-back, then 2nd eval surface, then outbound polish.

**Parallel tracks (D13):** Claude → steps 1–4 locally. Aarya/Arav → step 5 (Twilio/deploy) + chase Omni (O1). Merge on the `frames→text` contract.

### ⚠️ STILL UNVALIDATED (don't forget)
- **O1 Omni endpoint** — the whole "easy recognizer" bet. 30-min experiment, may fail → curated-clip fallback.
- **Outbound Twilio** — custom, not in starter; inbound is the safety net.
- **Cloud deploy** — required for ANY real phone leg; first deploy always has surprises. Do early enough to debug.
- **ASL recognition accuracy** — even Omni is unproven on ASL; curated clips guarantee the demo.
- **Latency** (G3) — sign→clip→Omni→Nemotron(thinking)→TTS→phone could be several seconds; acceptable? Measure once wired.

---

## 🛑 BUILD RULES (binding — Aarya, Arav, Claude all hold to these)

1. **TEST & PROVE AS WE BUILD.** Never just keep building. Loop: build → prove it works → prove OLD features still work → only THEN add the next thing. Every increment is demonstrated working before moving on.
2. **NO FLUFF, ONLY MVP.** Strip to the genuine MVP. A working *WOW* MVP that does the perfect amount, perfected and constantly tested (Rule 1), BEFORE adding anything new.
3. **UI/UX & DEMO IS KEY.** Must be demo-ready and fool-proof across ALL showcase conditions — judges want to see it genuinely working in every scenario and actually usable. The exact function must be *perfected*.
4. **MINDBLOWING + SIMPLE.** Doesn't need to do everything — but the one thing it does must be 100x better than what exists, or genuinely revolutionary / one-of-a-kind.
5. **USE & MAXIMIZE THE SPONSORS.** Deep-research sponsor capabilities, then actually manipulate/customize/build on them (weights, model config, custom metrics, etc.) — show we GENUINELY improved & personalized what was given.
6. **DO NOT GUESS.** Anything unclear / needing direction → ASK + deep-research sponsors/capabilities/stats BEFORE acting. Don't make product decisions unilaterally unless pre-authorized.
7. **HYPERFOCUS ON HACKATHON CRITERIA.** No random work. Fixate on excelling at what the judges reward (below).

## 🎯 HACKATHON WINNING CRITERIA (from starter README, line 30 — verbatim signals)
- **"great examples of using Cekura to IMPROVE voice agent performance"** → not run-once. Show **measure → fix → re-measure** (Cekura supports regression / side-by-side run comparison / custom metrics / 10k+ red-team scenarios). **A demo beat: before→after score improvement.**
- **"using open source models from NVIDIA"** → use Nemotron prominently. **Omni (open-weight, video) is MORE on-criteria than text Super** AND solves our recognizer. Double win.
- **"creativity / technically interesting / solves a real problem"** → ASL→phone accessibility hits "real problem" hard.

### Sponsor levers we can MAXIMIZE (Rule 5) — researched, not guessed
- **Nemotron `enable_thinking` toggle + sampling (temp/top_p/reasoning_budget).** Thinking ON ≈ +2.2s TTFB (measured in `nemotron_llm.py`!). For a LIVE PHONE CALL, latency is king → tune thinking per turn, **prove the latency win via Cekura latency metrics.** = "improved what was given" measured by Cekura. (Sources: vLLM Nemotron-3-Super cookbook, HF model card.)
- **Cekura custom metrics + regression + red-team** → our two-surface eval (D10) + a before/after improvement beat.
- **Nemotron Omni is open-weight on HF** (`nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning`) — video-capable. Chase the hosted endpoint (O1).

## How we collaborate
- Aarya + Arav. Keep this file as the single source of truth. Claude updates it as decisions land.
- Status legend: ✅ done · 🔨 building · ⏳ trying · ⛔ blocked · 🧠 design open
