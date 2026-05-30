# HANDSET — Execution Plan (deep)

**~1.5h to 6pm submission · two agents (Arav-Claude, Aarya-Claude) + two humans (Arav, Aarya)**

---

## 0. Verified state (honest, right now — not aspirational)

| Piece                                                                                    | State                                                                  | Owner  |
| ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------ |
| Sign recognition (`recognizer.js`: MediaPipe + per-user k-NN, ~66ms commits)             | ✅ physically verified by Arav + Aarya                                 | Arav-C |
| Conduct path (Nemotron expands noisy signs → sentence; `Z,O,L,O,F,T`→"refill my Zoloft") | ✅ proven on live endpoint                                             | Arav-C |
| Word-boost lexicon (`lexicon.py`)                                                        | ✅ unit-tested                                                         | Arav-C |
| UI (`signal-room.html` imports `recognizer.js`, one clean client)                        | ✅                                                                     | Aarya  |
| Bot `handset_bot.py` — **H1 gate**: WS sign → Gradium TTS (verbatim+conduct)             | ✅ local TTS · ⬜ **real Twilio call NOT wired**                       | Aarya  |
| Self-improvement harness (`improve_loop.py`)                                             | ⚠️ runs the full loop, scoring shows 0→0 (judge too strict)            | Arav-C |
| Omni eval (`omni_recognizer.py`, NVIDIA VL on AWS Bedrock)                               | ✅ live                                                                | Aarya  |
| Cekura                                                                                   | ⬜ plugin MCP 401; OAuth `cekura` server added, needs `/mcp` authorize | Arav   |

**The single thing that can sink us: the Twilio real-call leg (the GATE) is not done.** Everything else is testable up to it.

---

## 1. The product (one line + the hero)

**Handset** — a Deaf person signs to their phone; an agent **speaks their intent on a real phone call and _conducts_ it** (handles the receptionist's questions), replies come back as captions. **Hero moment: "I sign — and it makes the call."**

**Honest novelty (what we claim / don't):** it's NOT a word-for-word relay (that's Nagish, free) — it's an **agent that conducts transactional calls** (clinic/pharmacy/front-desk) **and learns your signs.** Do NOT claim friend-calls or continuous conversational ASL (unsolved + derivative). Frame: privacy/autonomy + the agent doing the work.

---

## 2. Architecture (data flow + every sponsor)

```
DEAF USER (Arav)                                          HEARING PARTY (phone)
   signs to camera                                              speaks
        │                                                          ▲
        ▼                                                          │
 ┌─────────────────────────────┐                                  │
 │ BROWSER (signal-room.html)  │  MediaPipe + per-user k-NN       │
 │ recognizer.js → sign token  │  (on-device, private)            │
 └─────────────┬───────────────┘                                  │
   WS {sign, mode:verbatim|conduct}                               │
                ▼                                                  │
 ┌─────────── handset_bot.py (Pipecat) ───────────────────────────┴───┐
 │ verbatim → fixed string                                            │
 │ conduct  → NEMOTRON-3-Super (intent→sentence, fixes fingerspelling)│  ← NVIDIA
 │   → TTSSpeakFrame → GRADIUM TTS → TWILIO call ════════════> PHONE  │  ← Twilio
 │ phone reply → NEMOTRON Speech ASR → lexicon.boost() → caption ─────┼─> browser
 └───────────────────────────────────────────────────────────────────┘  ← NVIDIA
   Hardened by CEKURA (adversarial receptionists). Omni-VL eval beat (AWS). AWS hosts Nemotron+Omni.
```

---

## 3. Toolbox (surfaced + mapped to tasks)

- **MCPs:** `cekura` (OAuth — the eval/self-improve engine) · `quorus-yc-dev` (room with Aarya, poll every turn) · Nemotron LLM+ASR + Omni-VL (HTTP).
- **Cekura skills (Loop B):** `cekura:cekura-create-agent` → `cekura:cekura-eval-design` → `cekura:run-evals` → `cekura:cekura-self-improving-agent`; agents `cekura:eval-suite-planner`, `cekura:metric-reviewer`.
- **Discipline skills:** `hackathon-sprint` (ONE feature, rehearse 5×, recorded backup) · `elite-debugging` (harness scoring, camera) · `verification-before-completion` (test before "done").
- **Roadmap-only (cite, don't build):** `nemo-speech-asr-finetune` (on-prem ASR fine-tune — needs GPU+dataset+time).
- **Agents available:** backend-engineer, frontend-engineer, general-purpose, Explore.

---

## 4. The two self-improvement loops (the crown theme — "eval data → better agent")

- **Loop A — per-user, on-device ("it learns YOU"):** k-NN sign-adaptation (`teachSign`) + **preset library + remap** + word-boost lexicon. Grows every use, private, no cloud.
- **Loop B — Cekura hardening, offline ("harder to hang up on"):** simulate adversarial receptionists → score the conduct agent → reflect → rewrite the prompt → re-run → **before/after completion card.** `improve_loop.py` proves it on Nemotron today; `cekura:cekura-self-improving-agent` is the official version.

### Cekura — exact steps (once `mcp__cekura__*` authed)

1. `cekura:cekura-create-agent` → register the conduct agent (text/prompt variant — no live bot needed).
2. `cekura:cekura-eval-design` → adversarial scenarios: robocall-skeptic, impatient, verification-gatekeeper.
3. `cekura:run-evals` → v0 scores.
4. `cekura:cekura-self-improving-agent` → diagnose → improve prompt → re-run → v1. Screenshot the before/after.
   **Fallback:** if Cekura keeps fighting auth, demo `improve_loop.py` (the loop, on Nemotron) + cite Cekura.

---

## 5. Demo script (~90s — winning structure, honest)

1. **0–10s** — open on the wound: "Today a Deaf person's phone call has a third person — a human interpreter — listening. Watch." (Handset idle, camera live.)
2. **10–40s** — Arav signs HELLO → APPOINTMENT → fingerspells a day; the agent **speaks it on a real call** to the front desk; the reply comes back as a caption. Latency HUD shows recognition ms.
3. **40–60s** — **customization beat:** "It doesn't know my sign for WATER — I teach it in 10 seconds." chip appears → signs it → spoken. (Loop A.)
4. **60–80s** — **self-improvement beat:** before/after card — "We ran adversarial receptionists through our loop; the agent went from X% to Y% completion." (Loop B.)
5. **80–90s** — land: "No interpreter. Your call, your language. On open NVIDIA models, hardened with Cekura."
   **De-risk:** recorded full-run backup (one keystroke), staged sign inputs (hotkeys), Chrome only, tether not venue wifi, real phone known-good + off-silent.

---

## 6. Who does what (next 1.5h)

- **Arav (human):** physical testing + accuracy feedback · `/mcp` reconnect+authorize `cekura` · capture preset signs (teach once → I export) · drive final rehearsal.
- **Arav-Claude (me):** fix `improve_loop.py` scoring · preset library + remap in `recognizer.js` · Cekura Loop B (once authed) · poll Quorus every turn.
- **Aarya + Aarya-Claude:** **Twilio real-call leg (THE GATE)** · live `reading` word render · hearing-side captions · Omni eval wiring.

---

## 7. Timeline

| Time       | Arav-Claude                                     | Aarya                     | Joint                                                    |
| ---------- | ----------------------------------------------- | ------------------------- | -------------------------------------------------------- |
| now → +30m | fix harness scoring (real climb) + preset/remap | **Twilio call leg**       | —                                                        |
| +30 → +60m | Cekura Loop B (authed) → before/after card      | captions back + live word | —                                                        |
| +60 → +80m | wire MediaPipe-vs-Omni into the eval beat       | UI polish                 | **repoint recognizer.js WS → bot; first real-call test** |
| +80 → +90m | —                                               | —                         | **rehearse 5× + record backup; submit**                  |

---

## 8. Risk register

| #   | Risk                                       | Sev      | Mitigation                                                                                              |
| --- | ------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------- |
| 1   | Twilio call leg not finished               | CRITICAL | Aarya whole-focus now; H1 (local TTS) already proven; if Twilio slips, demo on speakerphone as fallback |
| 2   | Recognition flaky under demo light         | HIGH     | staged-input hotkeys; teach demo vocab live; dark sleeves/bg; recorded backup                           |
| 3   | Cekura auth keeps failing                  | MED      | `improve_loop.py` IS the loop (no Cekura needed); cite Cekura                                           |
| 4   | App doesn't open at demo (the Tavril loss) | CRITICAL | recorded full-run backup, one keystroke away; rehearse 5×                                               |

---

## 9. Asks (to unblock me)

1. `/mcp` → reconnect+authorize **`cekura`** (OAuth) → Loop B goes official.
2. Capture the **preset signs** (teach the demo vocab once; I'll add the export).
3. Aarya: ping the second **sign-speaks-on-a-real-phone** passes → I repoint the WS.
