"""Multimodal example: ask Nemotron Omni about an image.

This is the capability that makes Nemotron *Omni* worth using over a plain
text LLM. Pass any public image URL or a local image as a data: URI.
"""

import base64
import mimetypes
import sys

from client import ask


def image_to_data_uri(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Local file path -> data URI
        url = image_to_data_uri(sys.argv[1])
        question = sys.argv[2] if len(sys.argv) > 2 else "Describe this image in detail."
    else:
        # Default: a public sample image. NOTE: the provider fetches remote URLs
        # server-side, so the host must allow non-browser requests (Wikimedia,
        # for example, returns 403). Passing a local file (data URI) always works.
        url = "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg"
        question = "What is in this image? Be specific."

    print(ask(question, image_urls=[url]))
