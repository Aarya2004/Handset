## What already exists (3-5 named)
1. **Nagish ($16M, 2024)** — autonomous AI relay that places real phone calls; the deaf user TYPES, an AI voice speaks it, and the hearing party's speech is transcribed back. Two-way, no human interpreter. TEXT-only — no ASL input.
2. **Sorenson "Sign Language AI"** (announced 2024) — real ASL recognition, but aimed at in-person kiosks/counters, POC stage, and structurally conflicted by their human-VRS (Video Relay Service) revenue. Not a consumer phone-call autonomy product.
3. **Google SignGemma / SignGemma-on-device** (2025) — an open sign-language-to-text MODEL. A capability, not a product; no telephony, no agent, no call orchestration.
4. **Sign-Speak / Signapse / Hand Talk** — sign recognition + signing-avatar APIs/SaaS. Components (recognition, avatar), not a calling agent; aimed at video captioning/translation, kiosks, web accessibility.
5. **Purple/ZVRS, Convo, and traditional VRS** — the incumbent model: a HUMAN interpreter on video relays your call. Exactly the "third person on my call" wound. FCC TRS-funded (~$1.5B/yr).

## Why those aren't enough (specific gaps)
- **Nagish** removes the human but forces TYPING — it ignores that ASL is the native, faster, emotionally-fluent language for ~250–500k ASL-primary Deaf people. Typing English is a second language for many. No ASL input = not autonomy in your own language.
- **Sorenson/SignGemma** stop at recognition→text. None close the loop to a live, conductable two-way phone call with a hearing party. SignGemma is a weight file; Sorenson is conflicted and not shipping consumer phone autonomy.
- **VRS incumbents** are the problem, not the solution: a human is always listening (privacy), supply is throttled (50:1 interpreter shortage, hold times), and the business model is structurally hostile to automating itself away.
- **Nobody fuses all three layers**: (a) ASL input, (b) an *agent that conducts the call* (phone trees, hold, intent-not-transcript), (c) a real two-way Twilio call with captioned replies. The novelty is the FUSION + the agent autonomy, not any single component.

## Proposed idea (one crisp paragraph)
An autonomous ASL phone agent: a Deaf user signs to their camera, on-device MediaPipe recognizes fingerspelling + a command vocabulary, and a Pipecat voice agent SPEAKS their intent onto a real Twilio phone call to any hearing party — then transcribes the reply into large live captions. Crucially it is not a word-for-word relay: the agent *conducts* the call (navigates phone trees, holds, handles back-and-forth), so the user signs INTENT, not every word. No human interpreter, no typing in a second language — privacy, autonomy, and ASL-as-first-language, on a phone the user already owns.

## Novelty score: 8.7 / 10
Justified: every component exists (recognition, Twilio, voice agents, captioning), so this is not a 10 — it's a **systems-integration + agent-autonomy** novelty, not a new-physics novelty. But the *specific fusion* — ASL-as-input + an autonomous call-conducting agent + a real two-way phone call — is not shipped by anyone. Nagish proved the "no-human-relay phone agent" market but left ASL on the table; Sorenson has ASL but is conflicted and kiosk-bound; SignGemma is a model. The agent-conducts-the-call layer (intent not transcript) is the genuinely defensible wedge and is absent from all prior art. Above the 8.5 bar, honestly — but the score rests on the agent-autonomy claim, so the demo MUST show the agent doing something a relay can't (handle a phone tree or a hold), not just speaking signed words.

## Three ways this fails
1. **Critical assumption — recognition is too brittle live.** MediaPipe fingerspelling + ~10 gestures may misfire under stage lighting/camera angle, and the "magic" collapses if the agent speaks garbage. *Mitigation:* scope to a rehearsed, high-confidence vocabulary; show a confidence gate (only speak above threshold); pre-seed the intent so a single clean sign triggers a full spoken sentence; mandatory recorded backup of a clean run.
2. **Market/ethical risk — Deaf community rejects hearing-built "fixes."** The signing-glove backlash and "Nothing About Us Without Us" mean a hearing team demoing an ASL product can read as appropriation or "repair." *Mitigation:* frame as autonomy/privacy infrastructure (removing the eavesdropping human), explicitly call ASL a full language, commit on-stage to Deaf co-design/Deaf leadership before any real deployment, and never imply you're "fixing" deafness.
3. **Execution risk — too many moving parts in 5h fail live.** Browser MediaPipe + Pipecat client message + Twilio + Nemotron + TTS is a long chain; any link breaks the hero moment (the April 23 lesson). *Mitigation:* ONE polished path (sign→speak→caption), separate browser process bridged via sendClientMessage→TTSSpeakFrame, confidence-gated, with a pre-recorded 90s backup that plays if anything stalls; freeze scope now, no avatar, no open-vocab.

## Ethical framing for the Deaf community

**Exact words to USE on stage:**
- "ASL is a complete, natural language — not English on the hands."
- "Today, making a phone call means a *third person* — a human interpreter — listens to your most private calls. We remove that person."
- "This is about **autonomy and privacy**: your call, your language, no one else in the room."
- "**Nothing about us without us** — this ships only with Deaf leadership and Deaf co-design. We're hearing builders; the Deaf community owns this direction."
- "We're not fixing anything about Deaf people. Deaf people aren't broken. We're fixing a broken *phone system*."
- "The user signs their *intent* in their *own language*."

**Words / poses to AVOID on stage:**
- Never: "cure," "fix," "restore," "help them hear," "give them a voice," "overcome their disability," "suffering," "impaired" as a noun.
- Never call ASL "gestures," "signing English," or imply it's a simplified/visual form of English.
- Don't say "the deaf" (use "Deaf people" / "the Deaf community").
- Avoid the savior pose: no "we built this FOR them" framing — it's WITH/BY-led. No hearing person signing badly as a punchline.
- Don't lead with the medical/disability frame; lead with the broken-phone-system + privacy frame.
- Don't overclaim full ASL translation — be honest it's fingerspelling + commands today, with Deaf-led roadmap to fluent ASL.

---
**GO** — at 8.7/10, above the 8.5 bar, conditional on the demo showing the *agent conducting the call* (not just speaking signed words) and the autonomy/privacy framing leading over any disability framing.