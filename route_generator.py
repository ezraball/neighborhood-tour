"""Route generator - creates random wander paths using OpenStreetMap data."""

import math
import random
import requests
from dataclasses import dataclass
from config import (
    GOOGLE_API_KEY,
    DEFAULT_RADIUS_METERS,
    TOTAL_ROUTE_METERS,
    SAMPLE_INTERVAL_METERS,
)


@dataclass
class RoutePoint:
    """A point along the route with position and viewing direction."""
    lat: float
    lng: float
    heading: float  # Direction to face (0-360, 0=North)


def get_walkable_streets(lat: float, lng: float, radius: int = DEFAULT_RADIUS_METERS) -> list[dict]:
    """
    Query OpenStreetMap Overpass API for walkable streets near a location.

    Args:
        lat: Center latitude
        lng: Center longitude
        radius: Search radius in meters

    Returns:
        List of way data with node coordinates
    """
    overpass_url = "https://overpass-api.de/api/interpreter"

    # For larger areas, query in chunks or use simpler query
    # Limit to main walkable streets for efficiency
    query = f"""
    [out:json][timeout:60];
    (
      way["highway"~"footway|pedestrian|residential|living_street|tertiary|secondary"](around:{radius},{lat},{lng});
    );
    out body;
    >;
    out skel qt;
    """

    try:
        response = requests.post(overpass_url, data={"data": query}, timeout=65)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        # Fall back to smaller radius if timeout or server error
        if radius > 400:
            print(f"  Request failed with {radius}m radius, trying {radius//2}m...")
            return get_walkable_streets(lat, lng, radius // 2)
        else:
            raise ValueError(f"Could not fetch street data: {e}")

    # Parse nodes into a lookup dict
    nodes = {}
    for element in data["elements"]:
        if element["type"] == "node":
            nodes[element["id"]] = (element["lat"], element["lon"])

    # Parse ways with their node coordinates
    ways = []
    for element in data["elements"]:
        if element["type"] == "way" and "nodes" in element:
            way_coords = []
            for node_id in element["nodes"]:
                if node_id in nodes:
                    way_coords.append(nodes[node_id])
            if len(way_coords) >= 2:
                ways.append({
                    "id": element["id"],
                    "coords": way_coords,
                    "tags": element.get("tags", {})
                })

    return ways


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in meters."""
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_heading(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate compass heading from point 1 to point 2 (0-360 degrees)."""
    delta_lng = math.radians(lng2 - lng1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    x = math.sin(delta_lng) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lng)

    heading = math.degrees(math.atan2(x, y))
    return (heading + 360) % 360


def interpolate_point(lat1: float, lng1: float, lat2: float, lng2: float, fraction: float) -> tuple[float, float]:
    """Interpolate a point between two coordinates."""
    lat = lat1 + (lat2 - lat1) * fraction
    lng = lng1 + (lng2 - lng1) * fraction
    return lat, lng


def generate_random_wander(
    start_lat: float,
    start_lng: float,
    radius: int = DEFAULT_RADIUS_METERS,
    target_distance: int = TOTAL_ROUTE_METERS
) -> list[RoutePoint]:
    """
    Generate a random wander route through nearby streets.

    Args:
        start_lat: Starting latitude (hotel location)
        start_lng: Starting longitude
        radius: Max distance to wander from start
        target_distance: Total route length in meters

    Returns:
        List of RoutePoints sampled along the route
    """
    print(f"Fetching walkable streets within {radius}m...")
    ways = get_walkable_streets(start_lat, start_lng, radius)

    if not ways:
        raise ValueError("No walkable streets found in this area")

    print(f"Found {len(ways)} walkable street segments")

    # Build a graph of connected points
    all_points = []
    for way in ways:
        all_points.extend(way["coords"])

    # Generate a wandering path by randomly selecting nearby street segments
    path_coords = [(start_lat, start_lng)]
    total_distance = 0
    visited_ways = set()

    current_lat, current_lng = start_lat, start_lng

    while total_distance < target_distance:
        # Find nearby ways we haven't fully explored
        candidates = []
        for way in ways:
            if way["id"] in visited_ways:
                continue
            for i, (lat, lng) in enumerate(way["coords"]):
                dist = haversine_distance(current_lat, current_lng, lat, lng)
                if dist < 200:  # Within 200m of current position
                    candidates.append((dist, way, i))

        if not candidates:
            # If no nearby unvisited ways, allow revisiting or pick random
            for way in ways:
                for i, (lat, lng) in enumerate(way["coords"]):
                    dist = haversine_distance(current_lat, current_lng, lat, lng)
                    if dist < 300:
                        candidates.append((dist, way, i))

        if not candidates:
            print(f"No more reachable streets at {total_distance}m, ending route")
            break

        # Weight selection toward closer points but allow some randomness
        candidates.sort(key=lambda x: x[0])
        top_candidates = candidates[:min(10, len(candidates))]
        _, selected_way, start_idx = random.choice(top_candidates)

        # Walk along this way
        coords = selected_way["coords"]

        # Decide direction (forward or backward along the way)
        if random.random() > 0.5:
            segment = coords[start_idx:]
        else:
            segment = coords[:start_idx + 1][::-1]

        for lat, lng in segment:
            dist = haversine_distance(current_lat, current_lng, lat, lng)
            if dist > 5:  # Only add if meaningful distance
                path_coords.append((lat, lng))
                total_distance += dist
                current_lat, current_lng = lat, lng

            if total_distance >= target_distance:
                break

        visited_ways.add(selected_way["id"])

    print(f"Generated path with {len(path_coords)} waypoints, {total_distance:.0f}m total")

    # Now sample points at regular intervals along this path
    route_points = sample_route_points(path_coords, SAMPLE_INTERVAL_METERS)
    print(f"Sampled {len(route_points)} points at {SAMPLE_INTERVAL_METERS}m intervals")

    return route_points


def sample_route_points(path_coords: list[tuple[float, float]], interval: int) -> list[RoutePoint]:
    """
    Sample points at regular intervals along a path.

    Args:
        path_coords: List of (lat, lng) coordinates forming the path
        interval: Distance between samples in meters

    Returns:
        List of RoutePoints with interpolated positions and headings
    """
    if len(path_coords) < 2:
        return []

    route_points = []
    accumulated_distance = 0
    next_sample_distance = 0

    for i in range(len(path_coords) - 1):
        lat1, lng1 = path_coords[i]
        lat2, lng2 = path_coords[i + 1]
        segment_distance = haversine_distance(lat1, lng1, lat2, lng2)

        if segment_distance < 0.1:  # Skip tiny segments
            continue

        segment_start = accumulated_distance
        segment_end = accumulated_distance + segment_distance

        # Sample points within this segment
        while next_sample_distance <= segment_end:
            if next_sample_distance >= segment_start:
                # Interpolate position within segment
                fraction = (next_sample_distance - segment_start) / segment_distance
                lat, lng = interpolate_point(lat1, lng1, lat2, lng2, fraction)

                # Calculate heading (direction of travel)
                heading = calculate_heading(lat1, lng1, lat2, lng2)

                route_points.append(RoutePoint(lat=lat, lng=lng, heading=heading))

            next_sample_distance += interval

        accumulated_distance = segment_end

    return route_points


if __name__ == "__main__":
    # Test with a London location
    test_lat, test_lng = 51.5074, -0.1278  # Central London
    points = generate_random_wander(test_lat, test_lng, radius=800, target_distance=1000)
    print(f"\nFirst 5 points:")
    for p in points[:5]:
        print(f"  {p.lat:.6f}, {p.lng:.6f} heading {p.heading:.1f}")
