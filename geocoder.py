"""Geocoding module - converts addresses to coordinates."""

import requests
from config import GOOGLE_API_KEY


def geocode_address(address: str) -> tuple[float, float]:
    """
    Convert an address string to latitude/longitude coordinates.

    Args:
        address: Human-readable address string

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        ValueError: If address cannot be geocoded
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK":
        raise ValueError(f"Geocoding failed: {data['status']} - {data.get('error_message', 'Unknown error')}")

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]


def reverse_geocode(lat: float, lng: float) -> str:
    """
    Convert coordinates to a street address/name.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Street name or address string
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        return "Unknown location"

    # Try to extract street name from address components
    for result in data["results"]:
        for component in result.get("address_components", []):
            if "route" in component["types"]:
                return component["long_name"]

    # Fallback to formatted address
    return data["results"][0].get("formatted_address", "Unknown location")


if __name__ == "__main__":
    # Quick test
    test_address = "10 Downing Street, London, UK"
    lat, lng = geocode_address(test_address)
    print(f"Address: {test_address}")
    print(f"Coordinates: {lat}, {lng}")
    print(f"Reverse: {reverse_geocode(lat, lng)}")
