import argparse
import json
import traceback

import google.generativeai as genai

from app.services.llm import parse_input
from app.utils.config import get_settings


def run_raw_gemini_check(prompt: str) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in .env before testing.")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    return {
        "model": settings.gemini_model,
        "raw_text": text,
    }


def run_parse_check(user_input: str) -> dict:
    parsed = parse_input(user_input)
    return {
        "activity": parsed.activity,
        "fallback_activity": parsed.fallback_activity,
        "weather_condition": parsed.weather_condition,
        "time": parsed.time,
        "city": parsed.city,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini + parser diagnostic for AI Day Planner")
    parser.add_argument(
        "--input",
        default="Plan a hiking trip in Pune this weekend, and if it rains suggest an indoor activity from 10 to 2",
        help="Natural language planning request",
    )
    parser.add_argument(
        "--raw-prompt",
        default="Reply with JSON only: {\"status\":\"ok\",\"service\":\"gemini\"}",
        help="Prompt used for direct Gemini connectivity check",
    )
    args = parser.parse_args()

    print("=== Gemini Diagnostic ===")
    print(f"Input: {args.input}")

    had_failure = False

    print("\n[1/2] Raw Gemini connectivity check...")
    try:
        raw_result = run_raw_gemini_check(args.raw_prompt)
        print(json.dumps(raw_result, indent=2))
    except Exception as exc:
        print(f"RAW GEMINI CHECK FAILED: {exc}")
        traceback.print_exc()
        had_failure = True

    print("\n[2/2] Planner parse_input check...")
    try:
        parse_result = run_parse_check(args.input)
        print(json.dumps(parse_result, indent=2))
    except Exception as exc:
        print(f"PARSE CHECK FAILED: {exc}")
        traceback.print_exc()
        had_failure = True

    if had_failure:
        print("\nOne or more checks failed.")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
