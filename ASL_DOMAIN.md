# ASL Domain Reference — for Handset

> Domain-expert reference so Claude/Codex can answer ASL-specific questions during
> implementation. Built from citation-backed research across four areas: linguistics &
> phonology, fingerspelling, sign-recognition ML (SLR/SLT), and Deaf culture/ethics.
> **Read the "Implications for Handset" callouts — they map linguistics → our architecture.**

Handset recap: browser captures signs (MediaPipe Hands 21 landmarks + per-user k-NN for
static signs; frame burst → NVIDIA VLM multiple-choice for motion signs; fingerspelling
letter-by-letter), an agent speaks the intent on a real Twilio call, the hearing reply
returns as captions (word-boosted ASR). Closed vocab. See `CONTEXT.md`.

---

## 0. The five-second version for implementers

1. **A sign = 5 simultaneous parameters: handshape, location, movement, palm orientation,
   non-manual markers (face/head).** Hand landmarks recover ~3 of them. **Movement** needs
   time (multiple frames). **Non-manual markers** (eyebrows, mouth, head) need the FACE —
   MediaPipe Hands is blind to it. This is the root cause of most hard cases.
2. **Single-frame k-NN structurally cannot tell apart signs that differ only by motion or
   only by face.** Route those away from k-NN. Don't put motion/face minimal pairs in vocab.
3. **Real fingerspelling is fast, cursive, coarticulated** — letters blend, never hit
   citation poses. Per-frame letter classification is the wrong primitive; the field uses
   sequence models + CTC. Our `T,H,U,R,S,D,A,Y` works only because the signer is slow/deliberate.
4. **Open-ended VLM prompting fails (returns UNKNOWN); multiple-choice works** — this is
   confirmed by the literature, not just our experience. Even the best VLM is ~30-35% top-1
   on motion signs *with* candidates. Use it as a constrained re-ranker, never an oracle.
5. **Ethics is load-bearing for the demo:** don't call it a "translator" or say it
   "understands ASL"; name the limits; involve a Deaf person; carve out medical/legal/911.

---

## 1. ASL Linguistics & Phonology

### ASL is a full natural language — not English on the hands
Own grammar (topic-comment, spatial verb agreement, aspect not tense). Not derived from
English; no reliable word-for-word mapping. Manually-coded English (SEE) is a separate
invented system, not ASL. ([Wikipedia ASL grammar](https://en.wikipedia.org/wiki/American_Sign_Language_grammar))

### The 5 phonological parameters (the building blocks)
Change one → different sign (or no sign). Stokoe originally proposed 3 (handshape, location,
movement); Battison added orientation; non-manuals added later. ([ASL phonology](https://en.wikipedia.org/wiki/American_Sign_Language_phonology), [HandSpeak](https://www.handspeak.com/learn/397/))

| Parameter | What it is | Recoverable from hand landmarks? |
|---|---|---|
| **Handshape** | finger configuration (>55 phonetic shapes; ~26 alphabet shapes are a *subset*) | **Yes** — k-NN strong here |
| **Location** | place on/near body (APPLE=cheek vs ONION=eye) | Partly — needs body-relative frame (Pose helps) |
| **Movement** | path movement (through space) vs internal (open/close, wiggle, rotate) | **No — needs temporal model** |
| **Palm orientation** | facing of the palm (BALANCE vs MAYBE) | Partly — **don't rotation-normalize it away** |
| **Non-manual markers** | eyebrows, mouth morphemes, head tilt/shake, body shift | **No — needs FACE capture** |

**Non-manual markers are grammar, not decoration:** raised eyebrows = yes/no question;
lowered = wh-question; head-shake = clausal negation; the "TH" mouth morpheme turns LATE into
NOT-YET. They scope over spans, not single frames.

### Minimal pairs — the killer problem for landmark-only recognition
Signs differing in exactly one parameter. Examples:

| Pair | Differs only by | Our system blind to it? |
|---|---|---|
| APPLE / ONION | location | partly |
| CAR / WHICH; SCHOOL / IMPOSSIBLE | handshape | no (k-NN handles) |
| TEMPORARY / TRAIN; BALANCE / MAYBE | palm orientation | only if we normalize orientation away |
| PROPOSE / MAYBE; AIRPLANE / FLY | **movement** (single vs repeated) | **YES — identical in any frame** |
| LATE / NOT-YET | **non-manual** (mouth morpheme) | **YES — identical in hands + motion** |

> **Implication for Handset:** Build an explicit "confusable cluster" list from minimal
> pairs and evaluate accuracy *within* clusters, not just global top-1 (global hides the
> exact failures that break comprehension). **Never put a movement-only or face-only minimal
> pair on the static k-NN path.** Don't fully rotation-normalize landmarks or you destroy
> the orientation contrast (TEMPORARY/TRAIN). Our current vocab (HELLO, YES, NO, THANK-YOU,
> APPOINTMENT, CANCEL, WAIT, REPEAT, WATER) is reasonably well-separated — keep auditing new
> additions for these traps.

### Battison's constraints (a free prior for two-handed signs)
- **Symmetry Condition:** if both hands move, they share handshape/orientation/movement.
- **Dominance Condition:** if the hands differ in handshape, only the dominant hand moves;
  the passive hand stays still and takes an **unmarked handshape** (only: A/S, B, 5, G/1, C, O).

> **Implication:** The passive hand is one of 6 easy shapes — high-confidence anchor to
> disambiguate the dominant hand. Detect dominant (moving) vs passive (static) hand;
> **mirror for left-handed signers** (capture handedness in per-user calibration). You can
> reject impossible configs (two different marked handshapes both moving) as tracking errors.

### Morphology lives in movement and space
- **Directional/indicating verbs** (GIVE, SHOW, PAY, HELP): move *between spatial loci* to
  mark subject/object — "I-give-you" vs "you-give-me" is the same handshape, opposite path.
- **Aspect** (no tense): encoded by movement change/reduplication.
- **Classifier predicates:** handshapes stand for object classes, then move through space —
  productive/open-class, NOT a fixed dictionary.
- **Numeral incorporation:** number handshape fuses into a sign (TWO-WEEK, 3-O'CLOCK).
- **Compounding** uses *hold deletion* — boundary between components is phonetically eroded.

> **Implication:** For directional verbs you must keep *absolute start/end loci* — don't
> center-normalize away spatial endpoints. Noun/verb and aspect distinctions are movement-only
> minimal pairs. Classifier predicates can't be enumerated by a closed set — out of scope for us.

### Syntax: topic-comment, flexible word order, grammar of space
Baseline SVO but OSV common under topicalization; **Time + Topic + Comment**. Order is
disambiguated by **non-manual marking**, not position. Signers set up **referent loci** in
space and point back to them (discourse-persistent — must be *remembered* across signs).

> **Implication:** Hands-only cannot tell a question from a statement or detect negation —
> sentence type rides on the face. Persistent spatial loci need discourse-level state, beyond
> per-sign classification. **This is why Handset is scoped to isolated intent signs +
> fingerspelling, not continuous ASL.** Our "conduct path" (Nemotron expands signed intent →
> natural sentence) is the right design: we recover *intent tokens*, the LLM supplies grammar.

### Notation systems
Stokoe (1960, ASL-specific, phonemic), **HamNoSys** (~210 symbols, language-agnostic, linear
→ most machine-friendly), SignWriting (pictographic, 2-D, hard to parse). If we ever want a
parameterized intermediate representation, HamNoSys is the tractable target.

---

## 2. Fingerspelling & the Manual Alphabet/Numbers

**Mental model:** letter-by-letter is the right model for the *writing system* but the wrong
architecture for the *signal*. Real fingerspelling is fast, cursive, coarticulated.

### Static vs movement letters; orientation-only pairs
- **24 letters are static handshapes; J and Z involve MOVEMENT** (traced in the air).
  **J = I-handshape + wrist twist** (I and J are the same shape — only motion differs).
  **Z = index finger tracing a zig-zag.**
- **Orientation-only pairs (same handshape):** **G/Q** (Q palm-down), **K/P** (P palm-down),
  **H/U** (H horizontal, U vertical). ([Lifeprint](https://www.lifeprint.com/asl101/pages-layout/fingerspelling.htm), [Wikipedia manual alphabet](https://en.wikipedia.org/wiki/American_manual_alphabet))

### Notoriously confusable letter families (for landmark models)
- **Fist family A/S/T/M/N/E** — differ only by **thumb placement / finger curl**; the thumb
  is often *occluded* in M/N/T so its landmark is hallucinated → confident wrong answers.
- **Two-finger family K/V/U/R/2** — differ by spread angle (U vs V), finger **crossing** (R,
  which breaks landmark fingertip ordering), thumb insertion + orientation (K/P).
- **D/F/G** — which fingers form the circle vs extend; lost under motion blur.

### Numbers overlap with letters
**2 = V, 6 = W, 9 = F, 10 ≈ A (thumb-up fist + shake).** Distinguished by **palm orientation**
(isolated numbers 1-5 are palm-BACK — opposite of letters which are palm-forward) and small
**internal motions** (6/9 taps, 10 shake). ASL "3" = thumb+index+middle (not the hearing "3").
Numbers flip palm orientation when sequenced (phone numbers, dates). ([Lifeprint numbers](https://www.lifeprint.com/asl101/pages-layout/numbersdiscussion.htm))

### Coarticulation — why per-frame classification fails
Letters blend bidirectionally; many target shapes are never fully reached; transitions
("movement epenthesis") carry information and get misread as spurious letters. Fluent
spelling is perceived as a **whole-word shape**, not decoded letter-by-letter.
([Jerde/Soechting/Flanders 2003](https://www.jneurosci.org/content/23/6/2383), [Shi et al. ASL-in-the-wild](https://arxiv.org/abs/1810.11438))

### Lexicalized fingerspelling (#JOB, #NO, #BUS, #BACK)
Fingerspelled loan-signs that have fused into signs: dropped letters, relocated, new movement.
`#JOB` ≈ J-twist-B, not J-O-B. **Never decodes correctly letter-by-letter** — handle as
whole-vocab entries. ([Lifeprint lexicalized](https://www.lifeprint.com/asl101/fingerspelling/fingerspellinglexicalized.htm))

### Double letters (LL, SS)
NOT two clean poses — signed as one shape + a **slide / bounce / tap-twice / arch** motion.
A per-frame classifier *under-counts* repeats → corrupts drug names ("amoxici**ll**in").

### Recognition reality
ChicagoFSWild SOTA is only **~42% letter accuracy in the wild** (CTC seq models). Per-frame
argmax does far worse on natural speed.

> **Implications for Handset (most relevant — we fingerspell names/days/drugs):**
> - Keep an **absolute palm-orientation feature + an internal-motion channel**; do NOT
>   rotation-normalize (needed for J/I, Z, G/Q, K/P, H/U, and number-vs-letter).
> - Add a **mode detector**: spelling vs numbers vs lexicalized sign (numbers flip palm rules).
> - Model **double letters** explicitly (slide/bounce/tap), or you'll drop repeats in drug names.
> - The tokens we fingerspell (names, drugs, addresses) are **OOV by nature** — least
>   language-model support, highest cost of a single-letter error. **Add a readback /
>   confirmation step** ("I heard V-I-C-O-D-I-N, correct?") and a drug/proper-noun lexicon for
>   constrained decoding. This pairs directly with our word-boosting lexicon (`lexicon.py`).
> - Expect the fist-family and two-finger-family to be our biggest error sinks; confidence
>   will be falsely high (gross shape right, sub-feature wrong).

---

## 3. Sign Recognition ML (SLR / SLT) — state of the art & honest limits

### Three tasks (hardest last)
- **ISLR** (isolated sign recognition): classify one pre-segmented sign. Easiest. **This +
  fingerspelling is what Handset actually is.**
- **CSLR** (continuous): transcribe unsegmented signing → glosses. Hard (segmentation +
  movement epenthesis + coarticulation are chicken-and-egg). **~19% WER even on clean,
  in-domain PHOENIX = ~1 in 5 glosses wrong.**
- **SLT** (translation): sign → fluent text (different grammar). BLEU in the ~20s, far below
  usable MT. **Open-vocab ASL→text in the wild is essentially not reliable today.**

### Accuracy is dominated by vocab size & signer-independence
~97% on 226-class AUTSL vs ~79% on 2000-class WLASL. Models trained signer-dependently
**collapse on unseen signers**. A 20-50 sign demo tells you almost nothing about 500+ behavior.
([WLASL](https://arxiv.org/pdf/1910.11006), [TwoStream 18.8% WER](https://arxiv.org/abs/2211.01367))

### Datasets closest to our setting
**PopSign** (phone selfie cam, 250 signs, Deaf signers) and **ASL Citizen** (in-home webcam,
2731 signs) — study these, not studio-clean PHOENIX. **ChicagoFSWild** for fingerspelling.

### MediaPipe Hands — what it captures and misses
21 3D landmarks/hand from one RGB frame. **z (depth) is an unreliable learned relative**,
not metric. **No face, no body pose** (need MediaPipe **Holistic** for those). Self-occlusion
and two-hand interaction cause tracking swaps. ([MediaPipe Hands](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md))

### Why static/single-frame is fundamentally limited
**Movement is a phoneme.** Min-pairs exist that share everything but movement → one frame
(or start+end pose) cannot separate them. Sequence models (LSTM/1D-temporal-conv/Transformer)
+ **CTC** (no frame-level labels needed) are the field standard.

### VLMs for sign recognition (2024-2025) — confirms our finding
Benchmark on WLASL-300: open-ended zero-shot Gemini-2.5-pro **23.65%** top-1; open-source
Qwen3-VL ~**0.45%** (refused 335 times); supervised baseline **~90%**. Giving the VLM the
**candidate list raised Gemini to 32.28%** — multiple-choice >> open-ended, exactly what we
saw. VLMs lack ASL priors, struggle with fine hand articulation, and show position bias.
([SLR in the Age of LLMs](https://arxiv.org/abs/2604.11225))

> **Implications for Handset:**
> - Our 3-tier split is sound: **k-NN-on-landmarks = static/handshape tier** (fast, low
>   latency); **VLM-on-frames = motion tier** (slow path); **fingerspelling = sequence tier**.
>   *As long as motion-dependent signs are routed away from single-frame k-NN.*
> - **Cheap win:** feed a landmark *trajectory* (16-32 normalized frames), not one frame, to
>   close k-NN's biggest blind spot (motion). Normalize (wrist-origin, hand-size scale) but
>   keep orientation.
> - **VLM tier hardening:** keep candidate list short & high-precision; **randomize candidate
>   order** (anti position-bias); include an explicit **"NONE / not a sign"** option; supply
>   *textual movement descriptions* per candidate (we already do this with SIGN_HINTS — good).
>   Treat VLM as best-effort, never authoritative; budget ~30-35% ceiling on motion signs.
> - **k-NN as personalization is principled, not a hack:** per-user enrollment sidesteps the
>   unsolved signer-independence gap and the long-tail — exactly the right call. Consider
>   metric-learning embeddings later for a better feature space, keeping the few-shot UX.
> - **Abstention cascade:** k-NN (gate on distance margin + absolute distance, require
>   temporal consistency over N frames) → if unsure escalate to VLM → if still unsure
>   **ask the user to repeat**. Confident-wrong is worse UX than "please repeat."
> - **Latency:** k-NN is sub-frame; VLM call is hundreds of ms–seconds. Only invoke VLM when
>   the cheap tier is uncertain; show interim feedback to hide VLM latency.

---

## 4. Deaf Culture, Accessibility & Ethics — guardrails for the product/demo

> This product sits on top of the single most-criticized genre of "Deaf tech" — the
> sign-recognition device hearing people build *for* Deaf people *without* Deaf people. The
> landmines are documented and avoidable.

### Terminology
- **Capital-D Deaf** = culture/community/identity; lowercase **deaf** = audiological. Also
  **Hard of Hearing, DeafBlind, DeafDisabled, Late-Deafened.** When unsure, ask how someone
  identifies. ([NAD FAQ](https://www.nad.org/resources/american-sign-language/community-and-culture-frequently-asked-questions/))
- **USE:** Deaf, deaf, hard of hearing, "ASL user," "ASL."
- **AVOID (NAD-flagged):** "deaf-mute"/"deaf and dumb," **"hearing-impaired"** (focuses on
  deficit, sets hearing as the standard), "the deaf," "suffers from," "gives voice to the
  voiceless," "empower the deaf," "fixed/solved deafness." Frame in the **cultural model**,
  not medical. **Audism** = treating hearing/speaking as superior or making the Deaf person
  bear the communication burden.

### ASL is not universal, and ASL ≠ signed English
300+ sign languages worldwide; ASL ≠ BSL (mutually unintelligible despite shared English),
related to LSF. **ASL ≠ SEE ≠ PSE.** Internal variation: **Black ASL**, regional, generational,
gendered — a model trained on one demographic fails others (accuracy *and* equity issue).
Say **"ASL (US)"**, not generic "sign language." ([NIDCD](https://www.nidcd.nih.gov/health/american-sign-language))

### Why naive sign-tech keeps failing/offending (the 30-yr "glove" hype cycle)
The canonical critique: ["Why Sign-Language Gloves Don't Help Deaf People"](https://allthingslinguistic.com/post/167390176466/why-sign-language-gloves-dont-help-deaf-people). Recurring failures:
1. **Ignoring non-manual grammar** (gloves/hands can't see the face — where grammar lives).
2. **Treating ASL as fingerspelling/isolated gesture** then marketing it as "translating ASL."
3. **One-directional design** (renders ASL→hearing, gives Deaf user nothing back).
4. **"Nothing About Us Without Us" violation** — built without Deaf collaborators.
5. **Solving the wrong problem** (Deaf people prioritize captioning, better interpreting —
   not gadgets that make them legible to hearing people).

### Existing relay infrastructure (don't over-claim against it)
FCC-regulated **TRS**: **VRS** (Deaf user ↔ human *qualified interpreter* who voices/signs),
IP Relay, **CapTel**. Interpreters are human, qualified, bound to accuracy/impartiality/
confidentiality ([47 CFR §64.604](https://www.law.cornell.edu/cfr/text/47/64.604)). **Handset is NOT VRS/TRS** — it's
assistive/augmentative. Never imply FCC certification, reimbursement, or interpreter-equivalence.

### Directionality & equity — both directions are first-class
Our reply→caption path has its own risk: **ASR mangles names/meds/dosages**, delivered as
confident caption text the Deaf user can't sanity-check against audio, with no back-channel
to notice. **Surface ASR uncertainty; flag low-confidence words; enable repair both ways.**
(This is exactly what our word-boosting `lexicon.py` targets — keep going.) Red flag: any
framing where "the Deaf user just signs more clearly for the machine" — that's the audist core.

### High-stakes contexts
NAD says even *human* VRI has limits in **medical/legal/emergency** — so an AI closed-vocab
tool is categorically unsuited there. **Explicitly out-of-scope medical/legal/911** in UI,
docs, and demo. Signing video is **biometric** — consent, encryption, minimal retention, no
training on user video without opt-in. Make **no accuracy claims you haven't measured.**

### Three things to fix before the demo (if nothing else)
1. **Stop calling it a "translator"/"understands ASL."** Say: *"recognizes a fixed set of ASL
   signs + fingerspelling to compose intent, which an agent voices on a call."* Name the
   non-manual-grammar + closed-vocab limits out loud — naming them defuses the #1 criticism.
2. **Show BOTH directions**, with caption uncertainty visible, and explicitly carve out
   medical/legal/emergency.
3. **Get a Deaf person involved and say so** — its absence is the one offense that has sunk
   every predecessor in this exact space.

> **Note on our framing (it's good):** `CONTEXT.md` already positions Handset as an agent that
> *conducts transactional calls* and expands *signed intent* (not a friend-relay, not
> continuous ASL). That's honest and dodges the biggest traps. The intent-token + LLM-grammar
> design is the right answer to "we can't recover ASL grammar from hands."

---

## Cross-cutting cheat sheet — what needs what

| Phenomenon | Hand landmarks? | Needs time (motion)? | Needs face/body? | Handset handling |
|---|---|---|---|---|
| Handshape | ✅ | — | — | k-NN |
| Palm orientation | partly (keep it!) | — | — | k-NN (don't normalize away) |
| Location | partly | — | Pose helps | k-NN / vocab choice |
| Movement (path/internal) | ❌ | ✅ | — | VLM tier / trajectory feature |
| Non-manual markers (grammar) | ❌ | ✅ (span) | ✅ | **out of scope** (Holistic future) |
| Verb agreement / loci | endpoints only | ✅ | Pose | out of scope (LLM supplies grammar) |
| Aspect / noun-verb | ❌ | ✅ | — | avoid such min-pairs in vocab |
| Fingerspelling letters (static) | ✅ | — | — | letter tier (+ orientation) |
| J, Z | ❌ | ✅ | — | needs motion — route to seq/VLM |
| Numbers vs letters (2/V, 6/W, 9/F) | partly | small motion | — | mode detector + orientation |
| Double letters | ❌ | ✅ | — | model slide/bounce/tap |
| Sentence type / negation | ❌ | ✅ | ✅ | **out of scope** (intent + LLM) |

---

## Source index (high-value)
- ASL phonology / grammar: [Wikipedia phonology](https://en.wikipedia.org/wiki/American_Sign_Language_phonology) · [Wikipedia grammar](https://en.wikipedia.org/wiki/American_Sign_Language_grammar) · [HandSpeak parameters](https://www.handspeak.com/learn/397/) · [Lifeprint linguistics](https://www.lifeprint.com/linguistics/)
- Fingerspelling: [Lifeprint fingerspelling](https://www.lifeprint.com/asl101/pages-layout/fingerspelling.htm) · [numbers](https://www.lifeprint.com/asl101/pages-layout/numbersdiscussion.htm) · [lexicalized](https://www.lifeprint.com/asl101/fingerspelling/fingerspellinglexicalized.htm) · [coarticulation (Jerde 2003)](https://www.jneurosci.org/content/23/6/2383) · [Shi et al. in-the-wild](https://arxiv.org/abs/1810.11438) · [ChicagoFSWild](https://home.ttic.edu/~klivescu/ChicagoFSWild.htm)
- SLR/SLT ML: [Sign Language Transformers](https://arxiv.org/pdf/2003.13830) · [Two-Stream Network](https://arxiv.org/abs/2211.01367) · [WLASL](https://arxiv.org/pdf/1910.11006) · [PopSign v1.0](https://signdata.cc.gatech.edu/res/doc/popsign_v1_0/popsign_v1_0_supplemental.pdf) · [ASL Citizen](https://papers.neurips.cc/paper_files/paper/2023/file/f29cf8f8b4996a4a453ef366cf496354-Paper-Datasets_and_Benchmarks.pdf) · [VLMs for SLR](https://arxiv.org/abs/2604.11225) · [MediaPipe Hands](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)
- Deaf culture / ethics: [NAD Community & Culture FAQ](https://www.nad.org/resources/american-sign-language/community-and-culture-frequently-asked-questions/) · [NAD VRI position](https://www.nad.org/resources/health-care-and-mental-health-services/video-remote-interpreting/) · [NIDCD What is ASL](https://www.nidcd.nih.gov/health/american-sign-language) · ["Why Sign-Language Gloves Don't Help"](https://allthingslinguistic.com/post/167390176466/why-sign-language-gloves-dont-help-deaf-people) · [FCC TRS](https://www.fcc.gov/consumers/guides/telecommunications-relay-service-trs) · [Black ASL](https://en.wikipedia.org/wiki/Black_American_Sign_Language) · [Nothing About Us Without Us](https://en.wikipedia.org/wiki/Nothing_about_us_without_us)

---

## Caveats / contested facts (don't overstate)
- **Handshape inventory count is genuinely contested** (Stokoe 19 cheremes; pedagogy "55+";
  linguistics ~30-40 contrastive) — cite a range, not one number.
- Unmarked handshape set (A/S, B, 5, G/1, C, O) is consistent across sources; "marked"
  examples vary by author.
- Battison's Symmetry/Dominance are solid; the 4-way Type 0-3 taxonomy should be confirmed
  against Battison (1978) before relying on it in code.
- Fingerspelling "in the wild" accuracy best cited as **~42% (Shi et al. 2018)**.
- Minimal-pair examples are standard textbook illustrations; exact articulation varies by
  dialect/signer.
