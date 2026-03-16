#!/usr/bin/env python3
"""
Test translation extraction logic without running the full LLM.
Run: python3 scripts/test_extract_translation.py
"""
import re
import sys
from pathlib import Path

# Add src so we can import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def strip_thinking(raw: str) -> str:
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()


def extract_translation(raw_response: str, original_text: str, to_lang: str) -> str:
    """Mirror of ChapterTranslator._extract_translation for testing."""
    if not (raw_response or "").strip():
        return ""
    out = raw_response.strip()
    out = strip_thinking(out)
    if f"Translation in {to_lang}:" in out:
        out = out.split(f"Translation in {to_lang}:")[-1].strip()
    elif "Translation:" in out:
        out = out.split("Translation:")[-1].strip()
    elif out.lower().startswith((f"{to_lang}:", f"{to_lang} ")):
        out = out.split(":", 1)[-1].strip() if ":" in out else out
    if original_text in out:
        after = out.split(original_text, 1)[-1].strip()
        if after:
            out = after
    out = out.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
    for prefix in ("Assistant:", "assistant:", "A:", "answer:", "Answer:"):
        if out.lower().startswith(prefix.lower()):
            out = out[len(prefix):].strip()
            break
    if not out and raw_response.strip():
        out = strip_thinking(raw_response.strip())
        out = out.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
    if not out and raw_response.strip():
        match = re.search(r"```(?:\w*)\s*\n(.*?)```", raw_response.strip(), re.DOTALL)
        if match:
            out = match.group(1).strip()
    if not out:
        out = strip_thinking(raw_response.strip())
        out = out.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
    return out


def main():
    original = "The wizard walked into the tower."
    cases = [
        # (raw_response, description)
        ("A srác belépett a toronyba.", "plain Hungarian only"),
        ("Translation in HU:\nA srác belépett a toronyba.", "with Translation in HU:"),
        ("Assistant: A srác belépett a toronyba.", "with Assistant: prefix"),
        ("<think>Need to translate...</think>\nA srác belépett a toronyba.", "thinking then text"),
        ("```hu\nA srác belépett a toronyba.\n```", "markdown code block"),
        ("A srác belépett a toronyba.<|im_end|>", "with im_end token"),
        ("  \n  A srác belépett a toronyba.  \n  ", "whitespace wrapped"),
        ("HU: A srác belépett a toronyba.", "HU: prefix"),
    ]
    ok = 0
    for raw, desc in cases:
        got = extract_translation(raw, original, "HU")
        valid = got and len(got) > 5 and "srác" in got or "torony" in got
        status = "OK" if valid else "FAIL"
        if valid:
            ok += 1
        print(f"  [{status}] {desc}")
        print(f"       -> {got[:80]!r}")
    print(f"\nResult: {ok}/{len(cases)} passed")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
