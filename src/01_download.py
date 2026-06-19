"""01 - Acquire source audio listed in sources.csv.

This is downstream of the *human* sourcing decision: you curate sources.csv by
auditioning candidates, then this script just fetches them.

sources.csv columns (see template):
  source_id, language, speaker_id, title, creator, url, license, type,
  local_path, clip_range, notes

  type:        youtube | url | local
  clip_range:  optional "HH:MM:SS-HH:MM:SS" to grab only a clean sub-range
"""
import csv
import shutil
import subprocess
import sys

import config
from utils import log


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def download_youtube(url: str, out_stem) -> None:
    """Download full best-audio in its native (compressed) format. Trimming to
    clip_range happens in 02_preprocess, which lets us use aria2c's parallel
    connections here to bypass YouTube's per-connection download throttling."""
    if not have("yt-dlp"):
        sys.exit("yt-dlp not installed - run: pip install yt-dlp")
    cmd = ["yt-dlp", "-f", "bestaudio", "-o", f"{out_stem}.%(ext)s", "--no-playlist"]
    if have("aria2c"):
        cmd += ["--downloader", "aria2c", "--downloader-args", "aria2c:-x16 -s16 -k1M"]
    cmd.append(url)
    log(f"  yt-dlp{' +aria2c' if have('aria2c') else ''} {url}")
    subprocess.run(cmd, check=True)


def main() -> None:
    if not config.SOURCES_CSV.exists():
        sys.exit(f"Missing {config.SOURCES_CSV}. Fill it in first.")
    config.RAW.mkdir(parents=True, exist_ok=True)

    with open(config.SOURCES_CSV, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("source_id", "").strip()
                and not r["source_id"].lstrip().startswith("#")]

    if not rows:
        sys.exit("sources.csv has no usable rows yet.")

    for r in rows:
        sid = r["source_id"].strip()
        out_stem = config.RAW / sid
        if any(config.RAW.glob(f"{sid}.*")):
            log(f"{sid}: already downloaded, skipping")
            continue
        stype = (r.get("type") or "youtube").strip().lower()
        log(f"{sid} [{r.get('language')}] {r.get('title','')}")
        try:
            if stype in ("youtube", "url"):
                download_youtube(r["url"].strip(), out_stem)
            elif stype == "local":
                src = r["local_path"].strip()
                shutil.copy(src, f"{out_stem}.wav")
                log(f"  copied local file {src}")
            else:
                log(f"  unknown type '{stype}', skipping")
        except subprocess.CalledProcessError as e:
            log(f"  FAILED ({sid}): {e}")

    log(f"Done. Raw audio in {config.RAW}")


if __name__ == "__main__":
    main()
