#!/usr/bin/env python3
"""
Neighborhood Tour Generator

Generates 1-minute flythrough videos of hotel neighborhoods using Google Street View.
Simulates a 1-hour walk compressed into a rapid video tour.

Usage:
    python main.py "123 Main St, London, UK"
    python main.py "Hotel Address" --output myhotel.mp4 --radius 1500
    python main.py --batch hotels.txt --output-dir ./tours/
"""

import argparse
import sys
from pathlib import Path

from config import (
    GOOGLE_API_KEY,
    DEFAULT_RADIUS_METERS,
    TOTAL_ROUTE_METERS,
    VIDEO_DURATION_SECONDS,
)
from geocoder import geocode_address
from route_generator import generate_random_wander
from streetview import fetch_images_for_route
from video_maker import create_flythrough_video, OUTPUT_DIR


def print_progress(current: int, total: int, prefix: str = ""):
    """Print a progress bar."""
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = "=" * filled + "-" * (bar_length - filled)
    percent = current / total * 100
    print(f"\r{prefix}[{bar}] {percent:.1f}% ({current}/{total})", end="", flush=True)
    if current == total:
        print()


def generate_tour(
    address: str,
    output_path: str = None,
    radius: int = DEFAULT_RADIUS_METERS
) -> str:
    """
    Generate a neighborhood tour video for an address.

    Args:
        address: Hotel/location address
        output_path: Output video path (optional, auto-generated if not provided)
        radius: Max wander distance from location in meters

    Returns:
        Path to the generated video
    """
    print(f"\n{'='*60}")
    print(f"Generating neighborhood tour for:")
    print(f"  {address}")
    print(f"{'='*60}\n")

    # Step 1: Geocode the address
    print("Step 1/4: Geocoding address...")
    try:
        lat, lng = geocode_address(address)
        print(f"  Location: {lat:.6f}, {lng:.6f}")
    except Exception as e:
        print(f"  ERROR: Could not geocode address: {e}")
        sys.exit(1)

    # Step 2: Generate walking route
    print(f"\nStep 2/4: Generating {TOTAL_ROUTE_METERS/1000:.1f}km walking route...")
    try:
        route_points = generate_random_wander(
            lat, lng,
            radius=radius,
            target_distance=TOTAL_ROUTE_METERS
        )
        print(f"  Generated {len(route_points)} waypoints")
    except Exception as e:
        print(f"  ERROR: Could not generate route: {e}")
        sys.exit(1)

    # Step 3: Fetch Street View images
    print(f"\nStep 3/4: Fetching Street View images...")

    def fetch_progress(current, total):
        print_progress(current, total, "  Fetching: ")

    try:
        images = fetch_images_for_route(route_points, progress_callback=fetch_progress)
    except Exception as e:
        print(f"\n  ERROR: Could not fetch images: {e}")
        sys.exit(1)

    # Step 4: Create video
    print(f"\nStep 4/4: Creating {VIDEO_DURATION_SECONDS}s flythrough video...")

    if output_path is None:
        # Generate filename from address
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in address)
        safe_name = safe_name[:50].strip()
        output_path = str(OUTPUT_DIR / f"{safe_name}.mp4")

    def video_progress(current, total):
        print_progress(current, total, "  Rendering: ")

    try:
        video_path = create_flythrough_video(
            images,
            output_path,
            progress_callback=video_progress
        )
    except Exception as e:
        print(f"\n  ERROR: Could not create video: {e}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Tour video created successfully!")
    print(f"  Output: {video_path}")
    print(f"{'='*60}\n")

    return video_path


def batch_generate(hotels_file: str, output_dir: str = None):
    """
    Generate tours for multiple hotels from a file.

    Args:
        hotels_file: Path to text file with one address per line
        output_dir: Directory to save videos (optional)
    """
    hotels_path = Path(hotels_file)
    if not hotels_path.exists():
        print(f"ERROR: Hotels file not found: {hotels_file}")
        sys.exit(1)

    addresses = [
        line.strip()
        for line in hotels_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    if not addresses:
        print("ERROR: No addresses found in file")
        sys.exit(1)

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = OUTPUT_DIR

    print(f"Generating tours for {len(addresses)} hotels...\n")

    results = []
    for i, address in enumerate(addresses, 1):
        print(f"\n[{i}/{len(addresses)}] Processing: {address}")
        try:
            safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in address)[:50]
            output_path = str(out_path / f"{safe_name}.mp4")
            video_path = generate_tour(address, output_path=output_path)
            results.append((address, video_path, None))
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append((address, None, str(e)))

    # Print summary
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for _, path, _ in results if path)
    print(f"Successful: {success}/{len(results)}")
    for address, path, error in results:
        status = f"OK: {path}" if path else f"FAILED: {error}"
        print(f"  {address[:40]}... {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate neighborhood flythrough videos from Google Street View",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "10 Downing Street, London, UK"
  python main.py "Hotel Address" --output hotel.mp4
  python main.py --batch hotels.txt --output-dir ./tours/
        """
    )

    parser.add_argument(
        "address",
        nargs="?",
        help="Hotel or location address to tour"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output video file path"
    )
    parser.add_argument(
        "--radius", "-r",
        type=int,
        default=DEFAULT_RADIUS_METERS,
        help=f"Max wander distance from location in meters (default: {DEFAULT_RADIUS_METERS})"
    )
    parser.add_argument(
        "--batch", "-b",
        help="Path to text file with addresses (one per line)"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for batch mode"
    )

    args = parser.parse_args()

    # Check API key
    if GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please set your Google API key")
        print("  Option 1: Set GOOGLE_API_KEY environment variable")
        print("  Option 2: Edit config.py and replace YOUR_API_KEY_HERE")
        sys.exit(1)

    if args.batch:
        batch_generate(args.batch, args.output_dir)
    elif args.address:
        generate_tour(args.address, args.output, args.radius)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
