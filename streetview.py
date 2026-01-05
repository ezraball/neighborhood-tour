"""Street View fetcher - downloads images with gap detection."""

import os
import hashlib
import requests
from pathlib import Path
from dataclasses import dataclass
from route_generator import RoutePoint
from config import (
    GOOGLE_API_KEY,
    STREETVIEW_SIZE,
    STREETVIEW_FOV,
    STREETVIEW_PITCH,
    CACHE_ENABLED,
)


@dataclass
class FetchedImage:
    """Represents a fetched image with metadata."""
    path: str
    lat: float
    lng: float
    heading: float
    is_streetview: bool  # False if it's a map fallback
    index: int


CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def get_cache_path(lat: float, lng: float, heading: float, is_streetview: bool) -> Path:
    """Generate a cache file path for an image."""
    key = f"{lat:.6f}_{lng:.6f}_{heading:.1f}_{'sv' if is_streetview else 'map'}"
    hash_key = hashlib.md5(key.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{hash_key}.jpg"


def check_streetview_coverage(lat: float, lng: float) -> bool:
    """
    Check if Street View imagery exists at a location.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        True if Street View coverage exists
    """
    url = "https://maps.googleapis.com/maps/api/streetview/metadata"
    params = {
        "location": f"{lat},{lng}",
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    return data.get("status") == "OK"


def fetch_streetview_image(lat: float, lng: float, heading: float) -> bytes:
    """
    Fetch a Street View image.

    Args:
        lat: Latitude
        lng: Longitude
        heading: Compass heading (0-360)

    Returns:
        Image bytes (JPEG)
    """
    url = "https://maps.googleapis.com/maps/api/streetview"
    params = {
        "location": f"{lat},{lng}",
        "size": STREETVIEW_SIZE,
        "heading": heading,
        "pitch": STREETVIEW_PITCH,
        "fov": STREETVIEW_FOV,
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.content


def fetch_map_image(lat: float, lng: float) -> bytes:
    """
    Fetch a satellite/map image as fallback for missing Street View.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Image bytes (PNG)
    """
    url = "https://maps.googleapis.com/maps/api/staticmap"
    params = {
        "center": f"{lat},{lng}",
        "zoom": 18,
        "size": STREETVIEW_SIZE,
        "maptype": "satellite",
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.content


def fetch_images_for_route(
    route_points: list[RoutePoint],
    progress_callback=None
) -> list[FetchedImage]:
    """
    Fetch Street View images for all points on a route.

    Args:
        route_points: List of RoutePoints to fetch images for
        progress_callback: Optional function(current, total) for progress updates

    Returns:
        List of FetchedImage objects
    """
    fetched = []
    total = len(route_points)
    streetview_count = 0
    map_count = 0

    for i, point in enumerate(route_points):
        if progress_callback:
            progress_callback(i + 1, total)

        # Check cache first
        sv_cache = get_cache_path(point.lat, point.lng, point.heading, True)
        map_cache = get_cache_path(point.lat, point.lng, point.heading, False)

        if CACHE_ENABLED and sv_cache.exists():
            fetched.append(FetchedImage(
                path=str(sv_cache),
                lat=point.lat,
                lng=point.lng,
                heading=point.heading,
                is_streetview=True,
                index=i
            ))
            streetview_count += 1
            continue

        if CACHE_ENABLED and map_cache.exists():
            fetched.append(FetchedImage(
                path=str(map_cache),
                lat=point.lat,
                lng=point.lng,
                heading=point.heading,
                is_streetview=False,
                index=i
            ))
            map_count += 1
            continue

        # Check if Street View coverage exists
        has_coverage = check_streetview_coverage(point.lat, point.lng)

        if has_coverage:
            # Fetch Street View image
            image_data = fetch_streetview_image(point.lat, point.lng, point.heading)
            cache_path = sv_cache
            is_streetview = True
            streetview_count += 1
        else:
            # Fallback to satellite map
            image_data = fetch_map_image(point.lat, point.lng)
            cache_path = map_cache
            is_streetview = False
            map_count += 1

        # Save to cache
        with open(cache_path, "wb") as f:
            f.write(image_data)

        fetched.append(FetchedImage(
            path=str(cache_path),
            lat=point.lat,
            lng=point.lng,
            heading=point.heading,
            is_streetview=is_streetview,
            index=i
        ))

    print(f"Fetched {streetview_count} Street View + {map_count} satellite images")
    return fetched


if __name__ == "__main__":
    # Quick test
    from route_generator import RoutePoint

    test_points = [
        RoutePoint(lat=51.5014, lng=-0.1419, heading=90),  # Buckingham Palace area
        RoutePoint(lat=51.5007, lng=-0.1246, heading=45),  # Westminster
    ]

    def progress(current, total):
        print(f"Fetching {current}/{total}...")

    images = fetch_images_for_route(test_points, progress_callback=progress)
    for img in images:
        print(f"  {img.path} - {'Street View' if img.is_streetview else 'Satellite'}")
