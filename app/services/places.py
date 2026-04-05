import requests

from app.models.schemas import PlaceOption
from app.utils.config import get_settings


def get_places(query: str, latitude: float | None = None, longitude: float | None = None) -> list[PlaceOption]:
    settings = get_settings()
    if not settings.google_places_api_key:
        raise ValueError("Missing GOOGLE_PLACES_API_KEY")

    lat = latitude if latitude is not None else settings.default_latitude
    lng = longitude if longitude is not None else settings.default_longitude

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
        )
        for place in top
    ]
