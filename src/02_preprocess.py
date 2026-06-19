"""02 - Standardize every raw source to a canonical format (and trim to clip_range).

Decision (see README Quality Targets): 24 kHz, mono, 16-bit PCM WAV.
We deliberately do NOT denoise here - aggressive denoising hurts naturalness,
which matters for TTS. We only convert format/rate, downmix to mono, trim to the
optional clip_range from sources.csv, and high-pass at 50 Hz to drop sub-sonic rumble.
"""
import csv
import shutil
import subprocess
import sys

import config
from utils import log


def clip_ranges() -> dict:
    """Map source_id -> 'HH:MM:SS-HH:MM:SS' from sources.csv (optional trims)."""
    out = {}
    if config.SOURCES_CSV.exists():
        with open(config.SOURCES_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                sid = (r.get("source_id") or "").strip()
                cr = (r.get("clip_range") or "").strip()
                if sid and cr:
                    out[sid] = cr
    return out


def main() -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not installed - run: brew install ffmpeg")
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    ranges = clip_ranges()

    raw_files = sorted(p for p in config.RAW.glob("*")
                       if p.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac", ".webm", ".opus"})
    if not raw_files:
        sys.exit(f"No raw audio in {config.RAW}. Run 01_download.py first.")

    for src in raw_files:
        out = config.PROCESSED / f"{src.stem}.wav"
        if out.exists():
            log(f"{src.stem}: already processed, skipping")
            continue
        trim, cr = [], ranges.get(src.stem, "")
        if cr and "-" in cr:
            start, end = cr.split("-", 1)
            trim = ["-ss", start, "-to", end]      # input-side seek; keeps [start, end]
        log(f"{src.stem}: -> {config.SAMPLE_RATE} Hz mono 16-bit{(' trim ' + cr) if cr else ''}")
        subprocess.run([
            "ffmpeg", "-y", *trim, "-i", str(src),
            "-ac", str(config.CHANNELS),
            "-ar", str(config.SAMPLE_RATE),
            "-af", "highpass=f=50",                # remove sub-sonic rumble only
            "-sample_fmt", "s16",
            str(out),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    log(f"Done. Standardized WAVs in {config.PROCESSED}")


if __name__ == "__main__":
    main()
