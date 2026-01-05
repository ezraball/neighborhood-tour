"""Configuration for neighborhood tour generator."""

import os

# Google API Key - set via environment variable or replace with your key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_API_KEY_HERE")

# Video settings
VIDEO_DURATION_SECONDS = 60  # Output video length
VIDEO_FPS = 30
SIMULATED_WALK_MINUTES = 60  # How much walking time to simulate
WALKING_PACE_METERS_PER_MIN = 80

# Route settings
SAMPLE_INTERVAL_METERS = 10  # Distance between Street View captures
DEFAULT_RADIUS_METERS = 800  # Max wander distance from hotel (auto-reduces if API slow)

# Street View image settings
STREETVIEW_SIZE = "640x480"
STREETVIEW_FOV = 100  # Field of view
STREETVIEW_PITCH = 5  # Slight upward angle to see buildings

# Derived calculations
TOTAL_ROUTE_METERS = SIMULATED_WALK_MINUTES * WALKING_PACE_METERS_PER_MIN  # ~4800m
TOTAL_IMAGES = TOTAL_ROUTE_METERS // SAMPLE_INTERVAL_METERS  # ~480

# Cache settings
CACHE_ENABLED = True
