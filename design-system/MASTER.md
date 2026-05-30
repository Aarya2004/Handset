# Handset — Design System (MASTER)

Source of truth for the Handset UI. Synthesized from the ui-ux-pro-max design intelligence + the PRD §9 spec. Aarya owns the visual layer; Arav owns recognition/logic that plugs into the marked hooks.

## North star (REVISED after v1 critique)
**A clean, humane, signing-first communication app** — in the lineage of Nagish / Ava / Google Live Transcribe: intentional, calm, the product feels native and modern, NOT "techy slop layered on old systems." The camera/hand feed is the hero surface; captions are a clean layer on it. Every element is purpose-built — no decorative chrome, no indicators for things that aren't happening.

**v1 was scrapped for being vibe-coded slop. The tells we are killing:**
- ❌ Mono font EVERYWHERE (the #1 slop tell) → mono is for NUMBERS ONLY now.
- ❌ Decorative indicators with no live data (fake waveform in standby, `—` HUD placeholders) → an indicator appears ONLY when its thing is live.
- ❌ Control-room grid backdrop, ops-dashboard density → gone. Calm and spacious.
- ❌ Two empty dark voids → ONE hero surface (camera), captions layered on it.

Design principle (from voice-AI UX research): **separate the conversation from the activity stream** — captions are the hero; agent status recedes to a quiet secondary line.

## Tokens

### Color (dark, status-driven; verified ≥4.5:1 text contrast)
```css
--base:      #0A0C10;  /* app background */
--panel:     #12151C;  /* cards / zones */
--hairline:  #1E2430;  /* borders, dividers */
--signal:    #3DF5C5;  /* YOU — cyan-green. Active recognition, your captions, speaking waveform. SCARCE = premium. */
--hearing:   #F5B23D;  /* THEM — amber. Aarya's captions. */
--text:      #E8EDF2;  /* primary text */
--text-dim:  #8A94A6;  /* secondary text */
--error:     #FF5C5C;  /* failures */
```
**The single most important UX rule: direction is color-coded. YOU = cyan, THEM = amber. Who is speaking is NEVER ambiguous.** Scarcity discipline: cyan appears ONLY on active-recognition / your-voice surfaces — never as generic accent.

### Typography — "Medical Clean" pairing (the skill's literal pick for accessibility)
```css
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');
--font: 'Figtree', system-ui, -apple-system, sans-serif;   /* EVERYTHING — headings, captions, labels, body */
--font-num: 'JetBrains Mono', ui-monospace, monospace;     /* ONLY latency numbers / measured values */
```
- **Figtree is warm, humane, highly readable** — chosen for Deaf-accessibility context.
- **Captions are the hero:** clamp ~32–60px, weight 600–700, `--font`.
- **Mono appears NOWHERE except actual measured numbers** (latency ms). This is the fix for the v1 mono-slop.
- Tabular figures for any number to prevent layout shift.

### Spacing & layout
- 4/8px rhythm. Section tiers 16/24/32/48. Container: full-bleed 16:9 control room.
- Three zones: top bar (call state + latency HUD + waveform) · main (camera+overlay 60% | sign profile 40%) · caption rail (bottom, both directions).

## Motion (premium 2D ONLY — NO three.js / particles / 3D; flagged as anti-pattern by skill + PRD)
Spring-based, max 1–2 active per view, ALL gated behind `prefers-reduced-motion`.
1. **Recognized pulse** — on confidence threshold cross: camera border cyan glow-pulse 200ms; token snaps `scale .9→1, opacity 0→1`, spring stiffness 400 / damping 28. Instant, not floaty.
2. **Caption slide-up** — new line `y:16,opacity:0`→settle; previous line dims to --text-dim; color-coded by speaker.
3. **Speaking waveform** — top-bar cyan bars driven by REAL TTS amplitude. Never fabricate the envelope — drive from audio or omit.
4. **Learned-a-sign (hero)** — new chip materializes with cyan sweep, counter rolls (11→12), toast "WATER added to your vocabulary." 1.2s, earned.
- Easing: ease-out entering, ease-in exiting. Exit ~60–70% of enter duration.
- The "3D-feeling" wow comes from the animated MediaPipe landmark-skeleton overlay (real + load-bearing), not bolted-on WebGL.

## Accessibility (THIS IS AN ASL PRODUCT — non-negotiable)
- Everything critical is visual + text; zero reliance on sound for the Deaf user.
- Captions ≥56px, AAA contrast, speaker-labeled AND color-coded (never color alone).
- `prefers-reduced-motion` respected everywhere. No flashing >3Hz. Generous timing.
- Latency HUD = REAL measured `performance.now()` delta, labeled "recognition". Never frozen/fabricated.

## Anti-patterns (do NOT)
- ❌ 3D effects / particle fields / react-three-fiber (cut: skill anti-pattern + PRD + Rule 2)
- ❌ complex shadows · ❌ emoji as icons (use Lucide/Heroicons SVG) · ❌ Inter font
- ❌ purple gradient / Inter-on-white / card-stack-on-lavender (AI-slop tells)
- ❌ faked telemetry / frozen latency number

## Integration contract (so Aarya's UI + Arav's recognition don't collide)
The visual layer exposes hooks; recognition calls them. Names locked:
- `SignalRoom.onSignRecognized(token, confidence)` → fires recognized-pulse + optimistic YOU caption
- `SignalRoom.onSpoken(text)` → YOU caption (cyan) + waveform
- `SignalRoom.onCaption(speaker, text)` → THEM caption (amber) when speaker==="aarya"
- `SignalRoom.onSignLearned(token)` → learned-a-sign hero animation + profile chip
- `SignalRoom.setCallState("ringing"|"connected"|"ended")` → top-bar indicator
Recognition/k-NN/enrollment internals stay Arav's; UI never touches them.
