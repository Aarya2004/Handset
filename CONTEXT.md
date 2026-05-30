# Handset — CONTEXT (team glossary + locked decisions)

> One link a Deaf person can use to make a real phone call: they sign, an agent
> speaks it on a real call, the reply comes back as live captions. No human
> interpreter.

## Locked decisions (don't re-litigate without flagging here)

- **Sign recognition runs ON-DEVICE in the browser (MediaPipe Hands + per-user k-NN).**
  WHY: the hosted **Nemotron-3-Super-120B is TEXT-ONLY** — it cannot see video. The only
  multimodal Nemotron is **Nano-Omni (30B)**, which is _smaller_ and _not hosted_.
  Server-side MediaPipe = same model + worse latency for zero gain. So on-device wins on
  accuracy, latency, privacy, and per-user learning. **Video-into-Pipecat for recognition
  is a dead end** (the model is blind). Aarya's VideoFrameProbe was a fine probe — but we
  do NOT pursue server-side recognition.
- **NVIDIA muscle goes on the HEARING side:** Nemotron-3-Super _conducts_ the call
  (expands signed intent → natural speech) and Nemotron Speech ASR transcribes the hearing
  party. We **customize** the ASR with **word boosting** (personal lexicon).
- **MVP = ONE feature:** committed sign → spoken on a real Twilio call → reply as captions.
- **Self-improvement = (1)** per-user sign profile (k-NN, learns YOUR signs live) **+ (2)**
  word-boosting lexicon (accurate captions on your words). Both are genuine per-user learning.

## Glossary

- **Client** — `client/index.html`, the browser app (Signal Room UI). Owns camera, MediaPipe,
  recognition, the Sign Profile, captions. Served static (localhost:5050).
- **Bridge** — `server/bridge_server.py`, a WebSocket the client sends sign tokens to.
  Currently speaks via macOS `say` (no-keys placeholder). Swaps to Pipecat `TTSSpeakFrame`.
- **Bot** — `server/bot-nemotron.py`, the Pipecat agent on the Twilio call.
- **Sign token** — a recognized label (e.g. `APPOINTMENT`) sent client→bot.
- **Hero path** — token → fixed verbatim phrase, spoken, no LLM (lowest risk).
- **Conduct path** — token → Nemotron expands to a natural sentence.
- **Word boosting** — biasing the hearing-side ASR toward the user's personal vocabulary.

## Product framing (refined)

This is an agent that **conducts transactional calls** (clinic/front-desk/pharmacy) — NOT a
friend relay. A friend relay = redundant with Nagish + needs unsolved continuous ASL. The
agent expands signed _intent_ and handles the receptionist's follow-ups. Hero path stays
verbatim for reliability; the conduct path is the non-redundant differentiator.

## Status (update as we go)

- ✅ Client recognition + "teach a sign" enrollment + latency HUD — built, JS parses clean.
- ✅ Bridge WS proven end-to-end (sign token → spoken aloud), no keys.
- ✅ **Conduct path (the AGENT differentiator)** — Nemotron expands noisy signs → real sentence,
  proven: "APPOINTMENT, T,H,U,R,Z,D,A,Y" → "I'd like to schedule an appointment for Thursday."
- ⬜ Real Twilio call leg (Aarya's bot — needs Twilio + Gradium keys).
- ⬜ Hearing-side ASR → captions (Aarya's bot).
- ⬜ Cekura before/after card (BLOCKED: needs CEKURA_API_KEY — MCP returns 401).
- ⬜ Word-boosting lexicon (after the hero loop is live).

## Stack & criteria

Build on **Pipecat**; **Twilio** = the call; **NVIDIA Nemotron** LLM+ASR = brain+ear;
**Cekura** = eval/hardening; **AWS** hosts the endpoints. Judges reward: strong Cekura usage
to improve the agent + genuine use/customization of the open NVIDIA models. See `PRD.md`.
