# Handset — End-to-End Test Protocol

Audience: **Arav** (recognition / client + Cekura), **Aarya** (bot / Twilio / UI). Run this **T-minus 1–2h** before the YC hackathon demo.

The chain that must work, end to end:

```
sign (camera) -> recognizer.js (per-user k-NN) -> WS {type:sign} -> handset_bot.py:8790
   -> Nemotron conduct (sentence) -> Gradium TTS -> Twilio outbound call -> receptionist answers
   -> receptionist speaks -> Nemotron ASR + lexicon boost -> WS {type:caption} -> signal-room.html caption
```

**Golden rule (from the chain-contract audit):** demo from **`client/signal-room.html`** with **`handset_bot.py` on port 8790** running. `signal-room.html:199` overrides `bridgeUrl` to `ws://localhost:8790/signal`; the bare default in `recognizer.js:58` is the stale `8787`. Do **NOT** open `client/index.html` — it is a divergent second client hardcoded to `8787` (the `say`-bridge) with a different conduct intent string and will make the phone path look dead.

---

## 1. MUST-FIX-BEFORE-DEMO (blocker / high only)

These are the only items that can break the live demo. Each is a real finding with file + minimal fix. Do these first, re-rehearse, then move on.

| #   | Sev                      | Symptom on stage                                                                                                                                      | File                                                                                    | Fix                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **BLOCKER**              | Signing the **same sign twice** in one sentence (YES then YES, WATER WATER) silently drops the 2nd.                                                   | `client/recognizer.js:211`                                                              | `bufferSign` returns early when `token===lastSign` and `lastSign` only resets in `commitSentence` (`:223`). Replace the equality guard with a **cooldown** using the already-declared `lastEmit`/`COOLDOWN` (`:34`,`:73`): allow the repeat if `now - lastEmit.t > COOLDOWN` **and** the hand dropped (vel ≥ HOLD_VEL since last emit). Simplest demo-safe fix: in `handleRecognize`, set `lastSign=null` whenever the hand moves (vel ≥ HOLD_VEL), so a deliberate re-raise re-fires. |
| 2   | **BLOCKER**              | Fluent signer (a new sign every <1.5s) → buffer never commits, **agent never speaks**, words pile up forever.                                         | `client/recognizer.js:216`                                                              | `pauseTimer` is cleared + re-armed on every sign with no cap. Add a hard cap in `bufferSign`: `if (sentBuf.length >= MAX_WORDS /*8*/) return commitSentence();` and/or track `sentenceStartT` and force-commit after a ceiling (~6000ms). Surface the existing `commitNow()` (`:347`) as a visible **Send** button fallback.                                                                                                                                                           |
| 3   | **HIGH**                 | `stop()` leaves a pending timer → `commitSentence` fires **after stop**, emits a stale sentence and leaks `sentBuf`/`lastSign` into the next session. | `client/recognizer.js:381`                                                              | In `stop()`: `clearTimeout(pauseTimer); pauseTimer=null; sentBuf=[]; lastSign=null;`. Add `if(!running) return;` at the top of `commitSentence` as defense-in-depth.                                                                                                                                                                                                                                                                                                                   |
| 4   | **HIGH**                 | Bridge mid-reconnect (2000ms backoff) when a sentence commits → intent **silently dropped**, buffer already cleared, UI stuck on "forming…".          | `client/recognizer.js` (`wsSend` `:204` no-ops when `readyState!==1`; commit at `:219`) | Add an outbound queue: if `wsSend` returns falsy, push the message to `pending[]` and flush `pending[]` in `bridge.onopen` (`:189`). Or, on send failure in `commitSentence`, restore `sentBuf` and `emit('error','offline — tap Send to retry')` so words aren't lost.                                                                                                                                                                                                                |
| 5   | **HIGH**                 | `video.play()` rejection swallowed → recognizer **frozen but says "ready"**, recognizes nothing, no error shown.                                      | `client/recognizer.js:311`                                                              | On `play()` failure emit `('error','camera autoplay blocked — tap to enable')` instead of swallowing. Add a watchdog: after ~1s running, if `lastVideoTime` never changed, `emit('error', 'no frames')`.                                                                                                                                                                                                                                                                               |
| 6   | **HIGH (ops, not code)** | Wrong page demoed → entire phone path appears dead.                                                                                                   | `client/index.html:597`                                                                 | **Operational, no code edit.** Confirm the open tab is `signal-room.html`. Close/quarantine `index.html`. Confirm `handset_bot.py` is the running backend on 8790 (not `bridge_server.py` on 8787).                                                                                                                                                                                                                                                                                    |

> Audit verdict: **no chain-breaking mismatch for the live demo** provided #6 holds. Items 1–5 are real recognizer demo-killers; fix in priority order, re-rehearse after each.

---

## 2. Layer-by-Layer Test Cases

Each: **Precondition / Steps / Expected / PASS-FAIL / Owner.** Run top to bottom; a failing lower layer invalidates the ones above it.

### L1 — Recognition (per-user k-NN, teach-a-sign, taught-vocab accuracy) — Owner: **Arav**

**T1.1 — Base vocab recognizes**

- Precondition: `signal-room.html` open, camera granted, recognizer `ready`, no custom signs taught (base library seeded via `seedFromDefault`).
- Steps: Sign each base token once, hold ~70ms: HELLO, APPOINTMENT, THURSDAY, YES, NO, THANK-YOU.
- Expected: `reading` shows the correct token at conf ≥ 0.7 (ACCEPT gate); `word` event fires for each.
- PASS/FAIL: PASS if ≥5/6 land correctly first try.

**T1.2 — Teach-a-sign (per-user enrollment)**

- Precondition: as above.
- Steps: Click **Teach**, name it `WATER`. Perform the sign through the 5-frame capture (`CAP_FRAMES=5`). Then sign WATER normally.
- Expected: After enroll, WATER recognizes at conf ≥ ACCEPT within 2–3 attempts; prototype stored in the per-user profile.
- PASS/FAIL: PASS if newly-taught WATER recognizes without a page reload.

**T1.3 — k-NN does not false-fire on the wrong user / empty profile**

- Precondition: fresh profile, nothing taught beyond base.
- Steps: Show a hand making a non-vocab shape.
- Expected: `reading` returns `token:null` or a low-conf token below ASK (0.45); no `word` emitted.
- PASS/FAIL: PASS if random hands do not spuriously commit a sign.

**T1.4 — Label sanitization (medium, guard against poisoned conduct)**

- Precondition: Teach flow.
- Steps: Try to teach a label containing a comma or spaces.
- Expected: label normalized to `[A-Z0-9-]`, comma stripped; empty-after-normalize rejected. (If unfixed, note as known-risk — comma in a label corrupts the `', '`-joined intent string at `recognizer.js:221`.)
- PASS/FAIL: PASS if no comma can reach the intent string.

### L2 — Sentence-buffering — Owner: **Arav**

**T2.1 — Accumulate + pause-commit (happy path)**

- Precondition: recognizer ready, bridge connected (`bridge:true`).
- Steps: Sign APPOINTMENT, then THURSDAY, then drop hands and wait > `PAUSE_MS` (1500ms).
- Expected: `word` fires per sign; after the pause, exactly ONE `sentence`/intent `"APPOINTMENT, THURSDAY"` is sent over WS; bot speaks one sentence.
- PASS/FAIL: PASS if a single combined sentence commits after the pause, not one-per-sign.

**T2.2 — Dedupe of a _held_ sign (must NOT double-fire)**

- Precondition: as above.
- Steps: Hold YES steady for 2s without dropping.
- Expected: YES fires **once**, not repeatedly.
- PASS/FAIL: PASS if a single steady hold = one token.

**T2.3 — Legitimate REPEAT (MUST-FIX #1 regression gate)**

- Precondition: MUST-FIX #1 applied.
- Steps: Sign YES, drop hand fully, re-raise and sign YES again, within the 1500ms window.
- Expected: buffer = `[YES, YES]`; both survive to commit.
- PASS/FAIL: **PASS only if the 2nd YES is NOT dropped.** (This is the canonical demo-failure case.)

**T2.4 — Rapid signs faster than 1.5s (MUST-FIX #2 regression gate)**

- Precondition: MUST-FIX #2 applied.
- Steps: Sign 9+ distinct tokens back-to-back, each < 1500ms apart (never pausing).
- Expected: commit fires at `MAX_WORDS` (8) or the elapsed ceiling — the agent **speaks** rather than buffering forever.
- PASS/FAIL: **PASS only if a sentence commits despite no natural pause.**

**T2.5 — Stop hygiene (MUST-FIX #3 regression gate)**

- Precondition: MUST-FIX #3 applied. Mid-sentence (buffer non-empty), call `stop()`.
- Expected: no `sentence` emitted after stop; next `start()` begins with an empty buffer.
- PASS/FAIL: PASS if no ghost sentence and no leaked state.

### L3 — Conduct (Nemotron sentence + fingerspelling) — Owner: **Arav**

**T3.1 — Intent → polite sentence**

- Precondition: bot on 8790, `enable_thinking:false` (`handset_bot.py:175`).
- Steps: Commit intent `"APPOINTMENT, THURSDAY"`.
- Expected: Nemotron returns one polite receptionist-facing sentence (e.g. "Hi, I'd like to book an appointment for Thursday."). Verbatim PHRASE tokens (`recognizer.js:43`) bypass the LLM and speak literally.
- PASS/FAIL: PASS if output is a single coherent sentence, no chain-of-thought leakage.

**T3.2 — Fingerspelling fix**

- Precondition: as above.
- Steps: Send a fingerspelled sequence (per-letter tokens).
- Expected: letters are joined into the intended word, not spoken letter-by-letter (per the fingerspelling note in `CONDUCT_SYSTEM`, `handset_bot.py:98`).
- PASS/FAIL: PASS if "T,H,U,R,S,D,A,Y" → "Thursday", not "T. H. U…".

### L4 — Telephony (real Twilio call answers + speaks the signed word) — Owner: **Aarya**

**T4.1 — Outbound call connects & speaks**

- Precondition: `TWILIO_*` + `GRADIUM_*` env set (`server/.env`); cloudflared tunnel up; `PUBLIC_HOST` known.
- Steps: `curl 'http://localhost:8790/call?public_host=<host>.trycloudflare.com'`. Answer `TWILIO_TO_NUMBER`. Then sign on the page.
- Expected: call connects; the signed/conducted sentence is spoken in the Gradium voice on the live call (Twilio media stream → `/twilio-media` `:241`).
- PASS/FAIL: PASS if the human on the phone hears the spoken sentence within ~2s of commit.

**T4.2 — `/say` smoke (telephony-independent TTS proof)**

- Precondition: bot running.
- Steps: `curl 'http://localhost:8790/say?text=Hello%20there'`.
- Expected: speaks "Hello there"; client gets `{type:spoken}` → YOU caption paints (`handset_bot.py:439`/`456`).
- PASS/FAIL: PASS if audio + YOU caption both appear. (Use this as the no-phone fallback.)

### L5 — Caption-back (Nemotron ASR + lexicon boost) — Owner: **Aarya**

**T5.1 — Receptionist reply becomes a caption**

- Precondition: live call up (T4.1), STT wired (`NVidiaWebSocketSTTService` → `CaptionEmitter` `:298`).
- Steps: The person on the phone says a sentence containing a lexicon word.
- Expected: inbound audio → VAD → STT → `boost(text, USER_LEXICON)` (`:159`) → `{type:caption, speaker:'aarya'}` (`:161`) → caption renders in `signal-room.html`.
- PASS/FAIL: PASS if the spoken reply appears as an "aarya" caption.

**T5.2 — Lexicon boost corrects a near-miss**

- Precondition: a session-specific word is in `USER_LEXICON` (`:122`).
- Steps: Have the caller say that word slightly mis-ASR'd.
- Expected: `boost()` snaps the raw ASR token to the lexicon word; corrected caption shown (raw logged at `:160`).
- PASS/FAIL: PASS if the boosted word is correct in the caption.

### L6 — Self-improvement (Cekura baseline-vs-GEPA + GEPA held-out + stress battery) — Owner: **Arav**

**T6.1 — GEPA held-out generalization (54 → 70)**

- Precondition: `server/optimizer/.venv` present; held-out intents are disjoint from train/val (`run_gepa.py:5`).
- Steps: `server/optimizer/.venv/bin/python server/optimizer/run_gepa.py`.
- Expected: prints baseline held-out then optimized held-out; optimized > baseline on intents GEPA never saw (target ~54→70).
- PASS/FAIL: PASS if optimized held-out beats baseline. Capture the printed numbers for the demo.

**T6.2 — Baseline-vs-GEPA conduct WS up**

- Precondition: `server/optimizer/.venv/bin/python server/cekura/conduct_ws.py` (PORT **8795**); `/baseline` = shipping `CONDUCT_SYSTEM`, `/gepa` = `optimized_prompt.txt`.
- Steps: Connect a probe to `ws://localhost:8795/baseline` and `/gepa`.
- Expected: both endpoints respond; routing per `route_path()` (`:85`).
- PASS/FAIL: PASS if both variants serve.

**T6.3 — Independent stress battery (15 adversarial personas)**

- Precondition: conduct WS up on 8795.
- Steps: `server/optimizer/.venv/bin/python server/cekura/stress_battery.py` (15 personas × baseline+gepa, real multi-turn WS, strict temp-0 Nemotron judge, [BOOKED]/[REFUSED] stripped before judging).
- Expected (measured, un-rigged): single fair N=15 run = **baseline 10/15, gepa 10/15** (aggregate dead heat). Across 3 runs (45 calls each): **baseline 27/45 (10,9,8), gepa 30/45 (10,10,10)** — GEPA +3 bookings and **lower variance**.
- **Honest framing for judges:** GEPA shows a _small, consistent_ edge (lower variance + clear wins on the adaptation/negotiation personas it was optimized for: verification-gatekeeper, monday-only-no-thursday, unrelated-security-question, full-then-waitlist), **not** a dramatic robustness win, against an already-strong baseline. Both reliably fail the hard-refuse personas (patient-must-be-on-line, no-third-party-calls, condescending-skeptic) — an honest agent weakness, not a test artifact. Do **not** overclaim.
- PASS/FAIL: PASS if it runs with zero call errors and reproduces GEPA ≥ baseline in aggregate.

---

## 3. ONE Full Happy-Path E2E Run-of-Show

Exact commands/URLs/ports. Run in order. Each `►` is a terminal/window.

```
► 1. START THE BOT (Twilio mode = default; do NOT set HANDSET_LOCAL_AUDIO)
   cd "/Users/aravkekane/YC Hack VA MAY26/handset/server"
   .venv/bin/python handset_bot.py
   # expect: "HANDSET bot on ws://localhost:8790/signal  [Twilio phone call (H2)]"

► 2. PUBLIC TUNNEL (Twilio must reach the media stream)
   cloudflared tunnel --url http://localhost:8790
   # copy the printed https host -> <HOST>.trycloudflare.com

► 3. SERVE THE CLIENT  (signal-room.html ONLY — never index.html)
   cd "/Users/aravkekane/YC Hack VA MAY26/handset/client"
   python3 -m http.server 5500
   # open  http://localhost:5500/signal-room.html
   # grant camera. Wait for recognizer "ready" and bridge:true (it overrides bridgeUrl -> 8790).

► 4. PLACE THE CALL
   curl 'http://localhost:8790/call?public_host=<HOST>.trycloudflare.com'
   # answer the phone that rings (TWILIO_TO_NUMBER)

► 5. SIGN -> SPEAK
   On the page: sign  APPOINTMENT  ...  THURSDAY  ... drop hands ~1.5s.
   # recognizer buffers -> commits ONE intent {type:sign} -> bot Nemotron-conducts
   # -> Gradium TTS -> Twilio -> the spoken sentence is heard on the live call.
   # YOU caption paints on the page (handset_bot.py:439).

► 6. TALK BACK -> CAPTION
   The person on the phone replies out loud.
   # inbound audio -> Nemotron ASR -> boost(text, USER_LEXICON) -> {type:caption, "aarya"}
   # the reply renders as an aarya caption in signal-room.html.

NO-PHONE FALLBACK (if Twilio/tunnel flakes):
   curl 'http://localhost:8790/say?text=Hello%20there'   # proves TTS + YOU caption without a call.
```

---

## 4. Demo GO / NO-GO Checklist (10 items)

Tick all **before** going live. Any NO-GO = do not start the demo.

1. [ ] Page open is **`signal-room.html`** (NOT `index.html`). Confirmed `bridgeUrl` → 8790.
2. [ ] `handset_bot.py` running on **8790**, banner shows **Twilio (H2)** mode (NOT `bridge_server.py`/8787, NOT LOCAL_AUDIO).
3. [ ] Camera granted; recognizer prints **`ready`**; video element is visible (NOT `display:none`).
4. [ ] Bridge shows **connected** (`bridge:true`).
5. [ ] MUST-FIX #1 (repeat-sign) verified via T2.3 — YES,YES survives.
6. [ ] MUST-FIX #2 (rapid commit cap) verified via T2.4 — agent speaks without a pause.
7. [ ] cloudflared tunnel live; `<HOST>` copied; `/call` returns no `error` JSON (Twilio + Gradium env set).
8. [ ] `/say` smoke passed (TTS + YOU caption) — fallback proven.
9. [ ] One full T4.1 → T5.1 dry run completed end-to-end on the real phone in the last 15 min.
10. [ ] **Backup video** of a clean E2E run is recorded, on disk, and openable offline.

---

## 5. Rehearse 5× + Record a Backup Video

- **Rehearse the full run-of-show (Section 3) five times back-to-back.** The April 23 hackathon was lost because the app wouldn't open at demo — muscle-memory the exact command order and the signal-room.html-only rule so a cold start under stage pressure is automatic.
- On the **cleanest run, screen-record the entire chain** (sign → spoken on phone → caption-back), audio included. This is item 10 of GO/NO-GO. If Twilio, the tunnel, the camera, or the network flakes on stage, **play the recording** and narrate live — never debug in front of judges.
- Keep the **`/say` no-phone fallback** one keystroke away as the intermediate safety net between "live call" and "play the video".
