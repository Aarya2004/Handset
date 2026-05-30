"""
test_vlm_signs.py — does NVIDIA Nemotron VL actually read ASL signs?

Captures frames from your Mac webcam while you hold a sign, sends them to the
VLM on Bedrock, prints the guess. The honest test of whether the VLM eval beat
can recognize signs at all.

  uv run python test_vlm_signs.py            # captures 4 frames over ~2s
  uv run python test_vlm_signs.py HELLO      # also tells you the intended sign

A small countdown gives you time to get the sign ready. Saves the frames to
/tmp/vlm_capture_*.jpg so you can see exactly what the model saw.
"""
import base64
import io
import sys
import time

import cv2
from PIL import Image

from omni_recognizer import recognize, MODEL_ID

INTENDED = sys.argv[1].upper() if len(sys.argv) > 1 else None
N_FRAMES = 4
SPREAD_SECS = 1.5  # capture window


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("✗ could not open webcam (grant camera permission to Terminal)")
        return
    # warm up the camera
    for _ in range(10):
        cap.read()
        time.sleep(0.03)

    print(f"\n=== VLM sign test (model: {MODEL_ID}) ===")
    if INTENDED:
        print(f"Intended sign: {INTENDED}")
    print("Get your sign ready. Capturing in...")
    for c in (3, 2, 1):
        print(f"  {c}...")
        time.sleep(1)
    print("  CAPTURING — hold the sign!")

    frames_b64 = []
    interval = SPREAD_SECS / N_FRAMES
    for i in range(N_FRAMES):
        ok, frame = cap.read()
        if not ok:
            continue
        # mirror (selfie) + downscale a touch for token budget
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img.thumbnail((640, 480))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b = buf.getvalue()
        img.save(f"/tmp/vlm_capture_{i}.jpg")
        frames_b64.append(base64.b64encode(b).decode())
        time.sleep(interval)
    cap.release()

    print(f"\nCaptured {len(frames_b64)} frames → /tmp/vlm_capture_*.jpg")
    print("Sending to NVIDIA VLM...\n")
    t0 = time.time()
    result = recognize(frames_b64)
    dt = int((time.time() - t0) * 1000)

    print("─" * 50)
    print(f"  VLM guess : {result.get('sign')!r}")
    print(f"  raw       : {result.get('raw')!r}")
    print(f"  latency   : {result.get('latency_ms', dt)} ms")
    if result.get("error"):
        print(f"  ERROR     : {result['error']}")
    if INTENDED:
        hit = (result.get("sign") or "").upper() == INTENDED
        print(f"  intended  : {INTENDED}  →  {'✓ MATCH' if hit else '✗ miss'}")
    print("─" * 50)


if __name__ == "__main__":
    main()
