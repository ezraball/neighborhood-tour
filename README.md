# Neighborhood Tour Generator

Generate 60-second flythrough videos of hotel neighborhoods using Google Street View. Quickly evaluate the vibe, safety, and walkability of areas before booking.

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What It Does

Given a hotel address, this tool:

1. **Generates a walking route** - Creates a ~4.8km random wander through nearby streets using OpenStreetMap data
2. **Captures Street View images** - Fetches ~480 images at 10-meter intervals along the route
3. **Creates a flythrough video** - Stitches images into a 60-second rapid tour (simulating a 1-hour walk at 60x speed)

## Example Output

```
$ python main.py "6 Hercules Rd, Lambeth, London SE1 7DP, UK"

============================================================
Generating neighborhood tour for:
  6 Hercules Rd, Lambeth, London SE1 7DP, UK
============================================================

Step 1/4: Geocoding address...
  Location: 51.498213, -0.113391

Step 2/4: Generating 4.8km walking route...
  Found 1803 walkable street segments
  Generated 481 waypoints

Step 3/4: Fetching Street View images...
  Fetching: [==============================] 100.0% (481/481)
  Fetched 481 Street View + 0 satellite images

Step 4/4: Creating 60s flythrough video...
  Created video: output/6 Hercules Rd_ Lambeth_ London SE1 7DP_ UK.mp4

============================================================
Tour video created successfully!
============================================================
```

## Prerequisites

- **Python 3.9+**
- **ffmpeg** - For video encoding
- **Google Cloud account** with billing enabled

### Required APIs

**Google Maps (required):**
- Geocoding API
- Street View Static API
- Maps Static API (for fallback satellite imagery)

**OpenRouteService (optional, recommended):**
- Walking isochrones - Defines the walkable area based on actual walking time rather than straight-line distance
- Free tier: 2,000 requests/day
- Sign up at [openrouteservice.org](https://openrouteservice.org/dev/#/signup)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ezraball/neighborhood-tour.git
cd neighborhood-tour
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
brew install ffmpeg  # macOS
```

### 3. Set up Google Cloud

Run the included setup script to create a project and enable APIs:

```bash
./setup-gcp.sh
```

Or manually:
1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable: Geocoding API, Street View Static API, Maps Static API
3. Create an API key
4. Enable billing (required for Maps APIs)

### 4. Configure API keys

```bash
# Required
export GOOGLE_API_KEY="your-google-api-key"

# Optional (enables walking isochrones for better route boundaries)
export ORS_API_KEY="your-openrouteservice-key"
```

Or edit `config.py` directly.

## Usage

### Single address

```bash
python main.py "123 Main St, London, UK"
```

### With options

```bash
python main.py "Hotel Address, City" \
  --output my-hotel.mp4 \
  --radius 1000  # Max wander distance in meters
```

### Batch mode

Create a `hotels.txt` file with one address per line:

```
Hotel A, 123 Main St, London, UK
Hotel B, 456 Oak Ave, London, UK
Hotel C, 789 Park Rd, London, UK
```

Then run:

```bash
python main.py --batch hotels.txt --output-dir ./tours/
```

## How It Works

### Route Generation

The tool determines the walkable area using one of two methods:

1. **Walking Isochrones (recommended)** - If `ORS_API_KEY` is set, uses OpenRouteService to calculate the actual area reachable within the walk time. This accounts for pedestrian paths, crossings, and terrain.

2. **Distance-based fallback** - If no ORS key is available, uses a simple radius around the hotel.

Once the walkable boundary is determined, the tool:

- Fetches street data from OpenStreetMap (via Overpass API)
- Filters to streets within the walkable area
- Generates a random wandering path (~4.8km total)
- Samples a point every 10 meters for Street View capture

### Image Capture

For each point along the route:

1. Check if Google Street View coverage exists at that location
2. If yes: Fetch a Street View image facing the direction of travel
3. If no: Fetch a satellite map image as fallback
4. Cache the image locally to avoid re-fetching

### Video Assembly

Images are assembled into a video using ffmpeg:

- 60 seconds total duration
- 30 fps output
- Each Street View location visible for ~0.125 seconds
- Progress bar overlay at the bottom
- "Satellite View" indicator when Street View coverage is missing

## Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `VIDEO_DURATION_SECONDS` | 60 | Output video length |
| `VIDEO_FPS` | 30 | Frames per second |
| `SIMULATED_WALK_MINUTES` | 60 | Virtual walk time to compress |
| `SAMPLE_INTERVAL_METERS` | 10 | Distance between captures |
| `DEFAULT_RADIUS_METERS` | 800 | Max wander distance from address |
| `STREETVIEW_FOV` | 100 | Field of view (degrees) |
| `STREETVIEW_PITCH` | 5 | Camera pitch (degrees upward) |

## Cost Estimate

Google Maps APIs have usage-based pricing with a $200/month free credit.

| API | Rate | Per Video (~481 calls) |
|-----|------|------------------------|
| Geocoding | $5/1000 | $0.005 |
| Street View metadata | Free | $0 |
| Street View images | $7/1000 | $3.37 |
| **Total** | | **~$3.38** |

With the $200 free monthly credit, you can generate approximately **59 videos per month at no cost**.

## Caching

Downloaded Street View images are cached in the `cache/` directory (~70KB each, ~35MB per video). Running the same address again will use cached images, saving both time and API costs.

## Project Structure

```
neighborhood-tour/
├── main.py              # CLI entry point
├── config.py            # Settings and API key
├── geocoder.py          # Address → coordinates
├── route_generator.py   # Random wander algorithm (uses OSM)
├── streetview.py        # Image fetching with gap detection
├── video_maker.py       # Video assembly with ffmpeg
├── setup-gcp.sh         # Google Cloud setup script
├── requirements.txt     # Python dependencies
├── cache/               # Cached Street View images (gitignored)
└── output/              # Generated videos (gitignored)
```

## Limitations

- **Street View coverage varies** - Some areas (especially private roads, new developments) may lack coverage
- **OpenStreetMap data quality** - Route quality depends on local OSM mapping
- **API rate limits** - Very large batch jobs may need throttling
- **Image age** - Street View images may be several years old

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- Google Maps Platform for Street View imagery
- OpenStreetMap contributors for street network data
- ffmpeg for video encoding
