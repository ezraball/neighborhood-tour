# Neighborhood Video Tour Generator - Work Plan

## Project Goal
Create a script that generates **1-minute sped-up video tours** of hotel neighborhoods using Google Street View, compressing a 1-hour walk into a rapid flythrough for quick neighborhood evaluation.

## Design Decisions

| Decision | Choice |
|----------|--------|
| Video format | **60x speedup** - 1 hour walk → 1 minute video |
| Walking pattern | **Random wander** - AI-picked interesting route based on nearby streets |
| Video transitions | **Smooth crossfade** - Blend between images for flowing, cinematic feel |
| Coverage gaps | **Show map view** - Display satellite/map view for missing sections |
| Audio | **No audio** - Silent video for simplicity |

## Video Math

| Metric | Value |
|--------|-------|
| Simulated walk time | 60 minutes |
| Output video length | 1 minute |
| Compression ratio | 60x |
| Walking pace | ~80 meters/min |
| Total route distance | ~4.8 km |
| Image sample interval | ~10 meters |
| Total images needed | ~480 |
| Video framerate | 30 fps |
| Images per second | ~8 (with crossfade blending) |

---

## Technical Approach

### Recommended Stack: Python
- **Why Python**: Rich ecosystem for APIs, image processing, and video generation
- **Key libraries**: `requests`, `opencv-python`, `Pillow`, `ffmpeg-python`

### Architecture Overview

```
[Address Input] → [Geocoding] → [Route Generation] → [Street View Images] → [1-min Flythrough]
                                       ↓                     ↓
                              [4.8km Random Wander]    [~480 images]
                                       ↓                     ↓
                              [Gap Detection → Satellite Fallback]
```

---

## Implementation Steps

### Phase 1: Setup & API Configuration

1. **Set up Google Cloud Project**
   - Create project at console.cloud.google.com
   - Enable these APIs:
     - Geocoding API
     - Directions API
     - Street View Static API
     - Maps Static API (for gap fallback images)
   - Create API key and set up billing (Street View API has costs after free tier)

2. **Project scaffolding**
   - Create Python virtual environment
   - Install dependencies: `requests`, `opencv-python`, `Pillow`, `ffmpeg-python`
   - Create config file for API keys

### Phase 2: Core Functionality

3. **Address to coordinates**
   - Use Geocoding API to convert hotel address → lat/lng
   - Validate the location has Street View coverage

4. **Random wander route generation**
   - Start at hotel location
   - Use OpenStreetMap data (via Overpass API) to get nearby walkable streets
   - Algorithm:
     1. Get all walkable paths within ~1.5km radius of hotel
     2. Pick random intersections as waypoints
     3. Use Directions API to create connected walking path
     4. Target ~4.8km total route (1-hour walk equivalent)
     5. Bias toward "interesting" streets (shops, landmarks) if data available
   - Sample points every ~10 meters along the route (~480 images total)

5. **Fetch Street View images with gap detection**
   - For each waypoint, call Street View Static API metadata endpoint first
   - If coverage exists: fetch image with parameters:
     - `location`: lat/lng
     - `heading`: Direction of travel (calculate from previous→next point)
     - `pitch`: 0 (level) or slight upward for buildings
     - `fov`: 90-120 for natural viewing
     - `size`: 640x480 or higher
   - If NO coverage: fetch Maps Static API satellite/map image instead
     - Mark as "gap" for video assembly

6. **Assemble rapid flythrough video**
   - Use ffmpeg/opencv to create 1-minute video
   - 480 images → 60 seconds @ 30fps = 1,800 frames
   - Each Street View location visible for ~3-4 frames (~0.125 sec)
   - Quick crossfade blending between consecutive images (2-3 blend frames)
   - For gap sections (map views):
     - Add subtle "No Street View" indicator overlay
   - Creates smooth, rapid "zoom through" effect
   - Output as MP4 (H.264)

### Phase 3: Enhancements

7. **Add metadata overlay**
   - Display current street name (from reverse geocoding)
   - Show distance from hotel
   - Add progress bar indicator

8. **Batch processing**
   - Accept list of hotel addresses from file
   - Generate comparison videos for each
   - Create summary report with thumbnail for each

---

## API Cost Considerations

| API | Free Tier | Cost After |
|-----|-----------|------------|
| Geocoding | $200/month credit | $5 per 1000 requests |
| Directions | $200/month credit | $5 per 1000 requests |
| Street View Static | $200/month credit | $7 per 1000 images |
| Maps Static | $200/month credit | $2 per 1000 images |

**Estimated cost per video:**
- 1-hour walk ≈ 4.8km ≈ ~480 images at 10m intervals
- Cost: ~$3.36 per neighborhood video (after free tier exhausted)
- First ~8-9 videos free with $200 credit

---

## File Structure

```
neighborhood-tour/
├── config.py              # API keys, default settings
├── main.py                # CLI entry point
├── geocoder.py            # Address → coordinates
├── route_generator.py     # Random wander algorithm
├── streetview.py          # Fetch images, detect gaps
├── video_maker.py         # Crossfade assembly
├── output/                # Generated videos
└── cache/                 # Cached images (avoid re-fetching)
```

---

## CLI Interface Design

```bash
# Basic usage (generates 1-min flythrough of 1-hour walk area)
python main.py "123 Main St, London, UK"

# With options
python main.py "123 Main St, London, UK" \
  --output hotel1.mp4 \    # Output filename
  --radius 1500            # Max wander distance from hotel (meters)

# Batch mode
python main.py --batch hotels.txt --output-dir ./tours/
```

---

## Next Steps

1. Create Google Cloud project and enable APIs
2. Implement geocoding module
3. Build random wander route generator using OSM data
4. Implement Street View fetching with gap detection
5. Build crossfade video assembly pipeline
6. Test with a known London hotel address
7. Iterate and refine based on video quality
