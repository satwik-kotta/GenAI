import requests

from app.utils.config import get_settings


def get_weather(city: str) -> str:
    settings = get_settings()
    if not settings.openweather_api_key:
        raise ValueError("Missing OPENWEATHER_API_KEY")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    condition = data["weather"][0]["main"]
    return "Rain" if "Rain" in condition else "Clear"
