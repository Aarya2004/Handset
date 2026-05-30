// Standalone logic test for the recognizer.js sentence-buffering fixes (no browser/MediaPipe).
// Replicates bufferSign/commitSentence/dedupe/caps EXACTLY and asserts the 4 bug fixes.
// Run: node client/_buffer_test.mjs
const PAUSE_MS = 1500,
  MAX_WORDS = 8,
  MAX_SENTENCE_MS = 6000;
let sentBuf = [],
  lastSign = null,
  pauseTimer = null,
  sentenceStartT = 0,
  running = true;
let now = 0;
const sent = []; // committed intents that reached the bridge
let bridgeUp = true;
let timers = [];
const setTO = (cb, ms) => {
  const t = { cb, ms };
  timers.push(t);
  return t;
};
const clearTO = (t) => (timers = timers.filter((x) => x !== t));
const firePause = () => {
  const t = pauseTimer;
  if (t && timers.includes(t)) {
    clearTO(t);
    t.cb();
  }
};
const wsSend = (o) => {
  if (bridgeUp) {
    sent.push(o.token);
    return true;
  }
  return false;
};
function bufferSign(token) {
  if (token === lastSign) return;
  lastSign = token;
  if (!sentBuf.length) sentenceStartT = now;
  sentBuf.push(token);
  clearTO(pauseTimer);
  if (sentBuf.length >= MAX_WORDS || now - sentenceStartT >= MAX_SENTENCE_MS) {
    commitSentence();
    return;
  }
  pauseTimer = setTO(commitSentence, PAUSE_MS);
}
function commitSentence() {
  if (!running) return;
  if (!sentBuf.length) return;
  clearTO(pauseTimer);
  const intent = sentBuf.join(", ");
  if (!wsSend({ token: intent })) {
    pauseTimer = setTO(commitSentence, 800);
    return;
  }
  sentBuf = [];
  lastSign = null;
  sentenceStartT = 0;
}
const handMove = () => (lastSign = null); // the handleRecognize else-branch reset
const reset = () => {
  sentBuf = [];
  lastSign = null;
  pauseTimer = null;
  sentenceStartT = 0;
  running = true;
  now = 0;
  bridgeUp = true;
  timers = [];
  sent.length = 0;
};
let pass = 0,
  fail = 0;
const ok = (c, m) =>
  c ? (pass++, console.log("✅", m)) : (fail++, console.log("❌", m));

// 1) Dedupe: same sign held (no hand move) fires ONCE.
reset();
bufferSign("YES");
bufferSign("YES");
firePause();
ok(
  sent.length === 1 && sent[0] === "YES",
  "held-sign dedupe: 'YES YES' (no move) -> one 'YES'",
);

// 2) Deliberate repeat: YES, hand moves, YES -> BOTH kept.
reset();
bufferSign("YES");
handMove();
bufferSign("YES");
firePause();
ok(sent[0] === "YES, YES", "deliberate repeat after hand-move: -> 'YES, YES'");

// 3) BLOCKER: fluent signing (new sign every <PAUSE_MS) still commits via MAX_WORDS cap.
reset();
for (let i = 0; i < 8; i++) {
  now += 200;
  bufferSign("S" + i);
}
ok(
  sent.length === 1 && sent[0].split(", ").length === 8,
  "MAX_WORDS cap: 8 fast signs auto-commit (never hangs)",
);

// 4) BLOCKER: MAX_SENTENCE_MS cap commits even if signs keep coming slowly.
reset();
bufferSign("A");
now = 6500;
bufferSign("B");
ok(sent.length === 1, "MAX_SENTENCE_MS cap: long sentence force-commits");

// 5) Bridge offline at commit: words RETAINED + retried, not lost.
reset();
bufferSign("REFILL");
bridgeUp = false;
firePause();
ok(
  sent.length === 0 && sentBuf.length === 1,
  "bridge offline: sentence retained, not dropped",
);
bridgeUp = true;
const retry = timers.find((t) => t.ms === 800);
retry && retry.cb();
ok(
  sent.length === 1 && sent[0] === "REFILL",
  "bridge back: retried commit delivers 'REFILL'",
);

// 6) stop() semantics: a pending commit must NOT fire after running=false.
reset();
bufferSign("HELLO");
running = false; // simulate stop()
firePause();
ok(sent.length === 0, "post-stop: pending commit does not fire");

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
