import os
import shutil
import subprocess

from .ui import Color, cprint

TARGET_SIZE = 640


def resize_square(filepath, size=TARGET_SIZE):
    if not filepath or not os.path.exists(filepath):
        return False

    try:
        temp_file = filepath + ".tmp.jpg"
        cmd = ["ffmpeg", "-y", "-i", filepath, "-vf", f"scale={size}:{size}", temp_file]
        result = subprocess.run(cmd, capture_output=True, timeout=10)

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            cprint(
                f"[thumbnail] ffmpeg error: {stderr}",
                Color.YELLOW,
            )
            return False

        shutil.move(temp_file, filepath)
        cprint(f"[thumbnail] ✓ Resized to {size}x{size}", Color.CYAN)
        return True

    except Exception as e:
        cprint(f"[thumbnail] ⚠ Failed to resize: {e}", Color.YELLOW)
        return False


def crop_to_square(filepath):
    if not filepath or not os.path.exists(filepath):
        return False

    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            cprint(f"[thumbnail] ffprobe error: {result.stderr.strip()}", Color.YELLOW)
            return False

        dims = result.stdout.strip()
        if "x" not in dims:
            return False

        width, height = map(int, dims.split("x"))

        if width == height == TARGET_SIZE:
            return True

        if width == height:
            crop_filter = f"scale={TARGET_SIZE}:{TARGET_SIZE}"
        elif width > height:
            crop_filter = (
                f"crop={height}:{height}:(iw-oh)/2:0,scale={TARGET_SIZE}:{TARGET_SIZE}"
            )
        else:
            crop_filter = (
                f"crop={width}:{width}:0:(ih-ow)/2,scale={TARGET_SIZE}:{TARGET_SIZE}"
            )

        temp_file = filepath + ".tmp.jpg"
        cmd = ["ffmpeg", "-y", "-i", filepath, "-vf", crop_filter, temp_file]
        result = subprocess.run(cmd, capture_output=True, timeout=10)

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            cprint(
                f"[thumbnail] ffmpeg error: {stderr}",
                Color.YELLOW,
            )
            return False

        shutil.move(temp_file, filepath)
        cprint(
            f"[thumbnail] ✓ Cropped and scaled to {TARGET_SIZE}x{TARGET_SIZE}",
            Color.CYAN,
        )
        return True

    except Exception as e:
        cprint(f"[thumbnail] ⚠ Failed to crop: {e}", Color.YELLOW)
        return False
