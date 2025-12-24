"""
Video Frame Extractor
Extracts key frames from video recordings for AI analysis.

Usage:
    python extract_video_frames.py <video_path> [interval_seconds]

This creates a folder with extracted frames that Claude can view.
"""

import cv2
import os
import sys
from pathlib import Path
from datetime import timedelta


def extract_frames(video_path: str, interval_seconds: int = 30, output_folder: str = None):
    """
    Extract frames from a video at regular intervals.

    Args:
        video_path: Path to the video file
        interval_seconds: Extract one frame every N seconds (default: 30)
        output_folder: Where to save frames (default: video_name_frames/)

    Returns:
        Path to output folder with extracted frames
    """
    video_path = Path(video_path)

    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return None

    # Create output folder
    if output_folder is None:
        output_folder = video_path.parent / f"{video_path.stem}_frames"
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # Open video
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"Error: Could not open video: {video_path}")
        return None

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"Video: {video_path.name}")
    print(f"Duration: {timedelta(seconds=int(duration))}")
    print(f"FPS: {fps:.1f}")
    print(f"Total frames: {total_frames}")
    print(f"Extracting every {interval_seconds} seconds...")
    print("-" * 50)

    # Calculate frame interval
    frame_interval = int(fps * interval_seconds)

    frame_count = 0
    extracted_count = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # Extract frame at interval
        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            timestamp_str = str(timedelta(seconds=int(timestamp))).replace(":", "-")

            # Save frame
            frame_filename = f"frame_{extracted_count:04d}_at_{timestamp_str}.jpg"
            frame_path = output_folder / frame_filename

            cv2.imwrite(str(frame_path), frame)
            print(f"  [{extracted_count+1}] Extracted at {timedelta(seconds=int(timestamp))}")

            extracted_count += 1

        frame_count += 1

    cap.release()

    print("-" * 50)
    print(f"Extracted {extracted_count} frames to: {output_folder}")

    # Create index file
    index_path = output_folder / "index.txt"
    with open(index_path, 'w') as f:
        f.write(f"Video: {video_path.name}\n")
        f.write(f"Duration: {timedelta(seconds=int(duration))}\n")
        f.write(f"Frames extracted: {extracted_count}\n")
        f.write(f"Interval: {interval_seconds} seconds\n")
        f.write(f"\nFrames:\n")
        for frame_file in sorted(output_folder.glob("frame_*.jpg")):
            f.write(f"  - {frame_file.name}\n")

    return str(output_folder)


def extract_all_videos_in_folder(folder: str, interval_seconds: int = 30):
    """Extract frames from all videos in a folder."""
    folder = Path(folder)
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.wmv']

    videos = []
    for ext in video_extensions:
        videos.extend(folder.glob(f"*{ext}"))
        videos.extend(folder.glob(f"*{ext.upper()}"))

    if not videos:
        print(f"No video files found in: {folder}")
        return []

    print(f"Found {len(videos)} video(s) in {folder}")
    print("=" * 50)

    output_folders = []
    for video in videos:
        print(f"\nProcessing: {video.name}")
        result = extract_frames(str(video), interval_seconds)
        if result:
            output_folders.append(result)

    return output_folders


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_video_frames.py <video_path_or_folder> [interval_seconds]")
        print("\nExamples:")
        print("  python extract_video_frames.py recording.mp4")
        print("  python extract_video_frames.py recording.mp4 60")
        print("  python extract_video_frames.py ./videos/")
        sys.exit(1)

    path = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    path = Path(path)

    if path.is_dir():
        extract_all_videos_in_folder(str(path), interval)
    else:
        extract_frames(str(path), interval)
