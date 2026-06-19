"""05 - Draft transcripts for every clip using Sarvam ASR (saaras:v3).

These are DRAFTS. The next step is you listening and correcting them - that
correction rate is one of the headline data-quality numbers in the report.
Reads data/segments.csv, writes data/transcribed.csv (adds asr_text).
"""
import csv
import sys

import config
from utils import log
import sarvam_client


def main() -> None:
    if not config.SEGMENTS_CSV.exists():
        sys.exit(f"Missing {config.SEGMENTS_CSV}. Run 04_segment.py first.")

    with open(config.SEGMENTS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out = []
    for i, r in enumerate(rows, 1):
        lang = r["language"]
        code = config.LANGUAGES.get(lang, config.LANGUAGES["en"])["sarvam_code"]
        path = config.ROOT / r["path"]
        try:
            res = sarvam_client.transcribe_clip(path, language_code=code)
            asr = res["transcript"].strip()
        except Exception as e:  # noqa: BLE001
            log(f"  ASR failed for {r['clip_id']}: {e}")
            asr = ""
        out.append({**r, "asr_text": asr})
        if i % 20 == 0:
            log(f"  transcribed {i}/{len(rows)}")

    fields = list(rows[0].keys()) + ["asr_text"]
    with open(config.TRANSCRIBED_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(out)
    log(f"Done. {len(out)} draft transcripts -> {config.TRANSCRIBED_CSV}")


if __name__ == "__main__":
    main()
