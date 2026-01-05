"""Video maker - assembles images into a crossfade flythrough video using ffmpeg."""

import os
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from streetview import FetchedImage
from config import VIDEO_FPS, VIDEO_DURATION_SECONDS, STREETVIEW_SIZE

# Parse video dimensions from config
VIDEO_WIDTH, VIDEO_HEIGHT = map(int, STREETVIEW_SIZE.split('x'))


OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def add_overlay_to_image(
    img: Image.Image,
    is_streetview: bool,
    progress: float
) -> Image.Image:
    """
    Add metadata overlay to an image.

    Args:
        img: PIL Image
        is_streetview: Whether this is Street View or satellite fallback
        progress: Progress through video (0.0 to 1.0)

    Returns:
        Image with overlay added
    """
    img = img.copy()
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Add "Satellite View" indicator for non-streetview images
    if not is_streetview:
        draw.rectangle([10, 10, 180, 40], fill=(0, 0, 0, 180))
        draw.text((15, 15), "Satellite View", fill=(255, 255, 255))

    # Add progress bar at bottom
    bar_height = 4
    bar_y = height - bar_height - 5
    bar_width = int(width * 0.8)
    bar_x = (width - bar_width) // 2

    # Background
    draw.rectangle(
        [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
        fill=(100, 100, 100)
    )
    # Progress fill
    fill_width = int(bar_width * progress)
    if fill_width > 0:
        draw.rectangle(
            [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height],
            fill=(255, 255, 255)
        )

    return img


def create_flythrough_video(
    images: list[FetchedImage],
    output_path: str,
    duration: int = VIDEO_DURATION_SECONDS,
    fps: int = VIDEO_FPS,
    progress_callback=None
) -> str:
    """
    Create a rapid flythrough video from Street View images using ffmpeg.

    Args:
        images: List of FetchedImage objects in route order
        output_path: Path to save the output video
        duration: Video duration in seconds
        fps: Frames per second
        progress_callback: Optional function(current, total) for progress updates

    Returns:
        Path to the created video file
    """
    if not images:
        raise ValueError("No images provided")

    num_images = len(images)

    # Create temp directory for processed frames
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Calculate timing
        total_frames = duration * fps
        frames_per_image = total_frames / num_images

        print(f"Preparing {num_images} images...")

        # Process each image and save with overlay
        frame_files = []
        for i, img_data in enumerate(images):
            if progress_callback:
                progress_callback(i + 1, num_images)

            progress = i / num_images

            # Load and resize image
            try:
                img = Image.open(img_data.path)
                img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
                img = img.convert('RGB')
            except Exception as e:
                # Create black placeholder
                img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))

            # Add overlay
            img = add_overlay_to_image(img, img_data.is_streetview, progress)

            # Save frame
            frame_path = temp_path / f"frame_{i:05d}.jpg"
            img.save(frame_path, "JPEG", quality=85)
            frame_files.append(frame_path)

        print(f"\nCreating video with ffmpeg...")

        # Calculate frame duration for ffmpeg
        # Each image should display for (duration / num_images) seconds
        frame_duration = duration / num_images

        # Create input file list for ffmpeg concat
        list_file = temp_path / "frames.txt"
        with open(list_file, "w") as f:
            for frame_path in frame_files:
                f.write(f"file '{frame_path}'\n")
                f.write(f"duration {frame_duration}\n")
            # Add last frame again (ffmpeg concat quirk)
            f.write(f"file '{frame_files[-1]}'\n")

        # Run ffmpeg with crossfade filter
        # Using concat demuxer with blend transition
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-vf", f"fps={fps},format=yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr}")
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    print(f"Created video: {output_path}")
    return output_path


if __name__ == "__main__":
    print("Video maker module loaded successfully")
    print(f"Output directory: {OUTPUT_DIR}")
