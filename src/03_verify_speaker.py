"""03 - Verify each source is single-speaker, using Sarvam diarization.

The assignment explicitly asks us to use Sarvam's diarization. We use it as a
*quality gate on our sourcing*: a clean single-speaker source should come back
almost entirely as one speaker. Where a second speaker appears (an interviewer,
an ad read, applause-laden Q&A), this report tells you where to trim or drop.

You still listen to the flagged regions yourself - this just points your ears.
Writes reports/diarization_report.csv.
"""
import csv
import json
import sys

import config
from utils import log
import sarvam_client


def language_map() -> dict[str, str]:
    out = {}
    if config.SOURCES_CSV.exists():
        with open(config.SOURCES_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                sid = (r.get("source_id") or "").strip()
                if sid and not sid.startswith("#"):
                    out[sid] = (r.get("language") or "en").strip()
    return out


def parse_speaker_durations(out_dir) -> dict[str, float]:
    """Sum spoken seconds per speaker label across the job's output JSON.
    Defensive against schema variations (turns / entries / diarized_transcript).
    """
    totals: dict[str, float] = {}
    for jf in out_dir.glob("*.json"):
        try:
            data = json.loads(jf.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            log(f"  could not parse {jf.name}: {e}")
            continue
        segments = (data.get("diarized_transcript", {}).get("entries")
                    or data.get("turns") or data.get("entries") or [])
        for s in segments:
            spk = str(s.get("speaker_id") or s.get("speaker") or "SPEAKER_00")
            start = float(s.get("start_time_seconds", s.get("start_time", s.get("start", 0)) or 0))
            end = float(s.get("end_time_seconds", s.get("end_time", s.get("end", 0)) or 0))
            totals[spk] = totals.get(spk, 0.0) + max(0.0, end - start)
    return totals


def main() -> None:
    langs = language_map()
    sources = sorted(config.PROCESSED.glob("*.wav"))
    if not sources:
        sys.exit(f"No processed audio in {config.PROCESSED}. Run 02_preprocess.py first.")

    rows = []
    for src in sources:
        lang = langs.get(src.stem, "en")
        code = config.LANGUAGES.get(lang, config.LANGUAGES["en"])["sarvam_code"]
        log(f"{src.stem}: diarizing (lang={code}) ...")
        try:
            out_dir = sarvam_client.diarize_source(src, language_code=code, num_speakers=2)
        except Exception as e:  # noqa: BLE001
            log(f"  diarization unavailable for {src.stem}: {e}")
            rows.append({"source_id": src.stem, "language": lang,
                         "n_speakers": "?", "dominant_share": "?", "verdict": "MANUAL"})
            continue
        totals = parse_speaker_durations(out_dir)
        total = sum(totals.values()) or 1.0
        dominant = max(totals.values()) / total if totals else 0.0
        verdict = "single-speaker OK" if dominant >= 0.95 else "REVIEW: multi-speaker"
        log(f"  speakers={len(totals)} dominant_share={dominant:.2%} -> {verdict}")
        rows.append({"source_id": src.stem, "language": lang,
                     "n_speakers": len(totals), "dominant_share": f"{dominant:.3f}",
                     "verdict": verdict})

    report = config.REPORTS / "diarization_report.csv"
    report.parent.mkdir(parents=True, exist_ok=True)
    with open(report, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source_id", "language", "n_speakers",
                                          "dominant_share", "verdict"])
        w.writeheader()
        w.writerows(rows)
    log(f"Done. Diarization report -> {report}")


if __name__ == "__main__":
    main()
