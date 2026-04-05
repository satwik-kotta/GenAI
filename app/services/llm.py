import json
import re

import google.generativeai as genai

from app.models.schemas import ParsedIntent
from app.utils.config import get_settings


def _extract_json_block(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model response did not include JSON")
    return json.loads(match.group(0))


def _fallback_parse(user_input: str) -> ParsedIntent:
    text = user_input.lower()

    activity = "Outdoor walk"
    fallback = "Cafe visit"

    if "hiking" in text:
        activity = "Hiking"
        fallback = "Indoor climbing"
    elif "beach" in text:
        activity = "Beach outing"
        fallback = "Mall visit"
    elif "football" in text or "cricket" in text:
        activity = "Sports session"
        fallback = "Indoor badminton"

    if "otherwise" in text and "indoor" in text:
        fallback = "Indoor activity"

    time_match = re.search(
        r"(\d{1,2})(?::\d{2})?\s*(am|pm)?\s*(?:to|-|until)\s*(\d{1,2})(?::\d{2})?\s*(am|pm)?",
        text,
    )
    time_text = time_match.group(0) if time_match else ("weekend" if "weekend" in text else None)

    return ParsedIntent(
        activity=activity,
        fallback_activity=fallback,
        weather_condition="Rain" if "rain" in text else None,
        time=time_text,
        city="Mumbai" if "mumbai" in text else None,
    )


def parse_input(user_input: str) -> ParsedIntent:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    genai.configure(api_key=settings.gemini_api_key)

    prompt = f"""
You are an information extraction engine.
Return only valid JSON with this exact schema:
{{
  "activity": "string",
  "fallback_activity": "string",
  "weather_condition": "string or null",
  "time": "string or null",
  "city": "string or null"
}}

User input: "{user_input}"
"""

    candidate_models = [
        settings.gemini_model,
        "models/gemini-2.0-flash",
        "models/gemini-flash-latest",
        "models/gemini-pro-latest",
    ]

    last_error = None
    response = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            break
        except Exception as exc:
            last_error = exc

    if response is None:
        return _fallback_parse(user_input)

    parsed = _extract_json_block(response.text)

    return ParsedIntent(
        activity=parsed.get("activity", "Outdoor activity"),
        fallback_activity=parsed.get("fallback_activity", "Indoor activity"),
        weather_condition=parsed.get("weather_condition"),
        time=parsed.get("time"),
        city=parsed.get("city"),
    )
