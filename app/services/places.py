import requests

from app.models.schemas import PlaceOption
from app.utils.config import get_settings


def _resolve_coordinates_from_city(city: str, api_key: str) -> tuple[float, float] | None:
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geocode_params = {
        "address": city,
        "key": api_key,
    }

    response = requests.get(geocode_url, params=geocode_params, timeout=15)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if not results:
        return None

    location = results[0].get("geometry", {}).get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def get_places(
    query: str,
    latitude: float | None = None,
    longitude: float | None = None,
    city: str | None = None,
) -> list[PlaceOption]:
    settings = get_settings()
    if not settings.google_places_api_key:
        raise ValueError("Missing GOOGLE_PLACES_API_KEY")

    lat = latitude
    lng = longitude

    if lat is None or lng is None:
        if city:
            resolved = _resolve_coordinates_from_city(city, settings.google_places_api_key)
            if resolved is not None:
                lat, lng = resolved

    if lat is None or lng is None:
        lat = settings.default_latitude
        lng = settings.default_longitude

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 5000,
        "keyword": query,
        "key": settings.google_places_api_key,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    results = data.get("results", [])
    ranked = sorted(results, key=lambda item: item.get("rating", 0), reverse=True)

    top = ranked[:3]
    return [
        PlaceOption(
            name=place.get("name", "Unknown place"),
            address=place.get("vicinity"),
            rating=place.get("rating"),
            place_type=(place.get("types") or [None])[0],
        )
        for place in top
    ]
