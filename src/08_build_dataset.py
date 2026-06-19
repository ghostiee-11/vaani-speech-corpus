"""08: Assemble the curated clips into a HuggingFace dataset and (optionally) push.

Joins your curated review_sheet.csv (keep=Y) with qc_report.csv (qc_pass=Y) and
the source licences from sources.csv, builds a `datasets` object with an Audio
column, writes a local export (clips + metadata.csv + a rich dataset card), and
pushes to the Hub if HF_TOKEN + HF_DATASET_REPO are set.
"""
import csv
import os
import shutil
import sys
from collections import defaultdict

import config
from utils import load_env, log


def load_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    load_env()
    for p in (config.REVIEW_CSV, config.QC_CSV, config.SOURCES_CSV):
        if not Path(p).exists():
            sys.exit(f"Missing {p}. Complete earlier steps first.")

    review = {r["clip_id"]: r for r in load_csv(config.REVIEW_CSV)
              if (r.get("keep") or "").upper() == "Y"}
    qc = {r["clip_id"]: r for r in load_csv(config.QC_CSV)}
    src = {r["source_id"]: r for r in load_csv(config.SOURCES_CSV)
           if (r.get("source_id") or "").strip()}

    records = []
    for cid, r in review.items():
        q = qc.get(cid)
        if not q or q.get("qc_pass") != "Y":
            continue                      # only QC-passing, human-kept clips ship
        source_id = cid.rsplit("_", 1)[0]   # clip_id == "<source_id>_NNN"
        s = src.get(source_id, {})
        records.append({
            "audio": str(config.ROOT / r["path"]),
            "text": r["text"].strip(),
            "normalized_text": r["normalized_text"].strip(),
            "language": r["language"],
            "speaker_id": r["speaker_id"],
            "emotion": r["emotion"].strip().lower(),
            "intensity": r.get("intensity", "medium").strip().lower(),
            "duration_sec": float(q["duration_sec"]),
            "sample_rate": int(q["sample_rate"]),
            "snr_db": float(q["snr_db"]) if q["snr_db"] not in ("nan", "") else None,
            "lufs": float(q["lufs"]),
            "source_id": source_id,
            "source_url": s.get("url", ""),
            "license": s.get("license", config.DATASET_LICENSE),
        })

    if not records:
        sys.exit("No clips passed both human keep=Y and QC. Nothing to build.")

    _write_local_export(records)
    card = _dataset_card(records)
    (config.ROOT / "DATASET_CARD.md").write_text(card, encoding="utf-8")

    _maybe_push(records, card)


def _write_local_export(records: list[dict]) -> None:
    export = config.DATA / "hf_export"
    if export.exists():
        shutil.rmtree(export)
    (export / "audio").mkdir(parents=True)
    meta_fields = [k for k in records[0] if k != "audio"]
    with open(export / "metadata.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file_name"] + meta_fields)
        w.writeheader()
        for rec in records:
            fn = f"audio/{Path(rec['audio']).name}"
            shutil.copy(rec["audio"], export / fn)
            w.writerow({"file_name": fn, **{k: rec[k] for k in meta_fields}})
    log(f"  local export -> {export}")


def _maybe_push(records: list[dict], card: str) -> None:
    repo = os.environ.get("HF_DATASET_REPO")
    token = os.environ.get("HF_TOKEN")
    if not (repo and token):
        log("  HF_TOKEN / HF_DATASET_REPO not set, skipping push.")
        log("  To publish: set them in .env, then re-run this script.")
        return
    from datasets import Dataset, Audio
    from huggingface_hub import HfApi

    ds = Dataset.from_list([{k: v for k, v in r.items()} for r in records])
    ds = ds.cast_column("audio", Audio(sampling_rate=config.SAMPLE_RATE))
    log(f"  pushing {len(records)} rows to https://huggingface.co/datasets/{repo}")
    ds.push_to_hub(repo, token=token, private=False)
    HfApi(token=token).upload_file(
        path_or_fileobj=card.encode("utf-8"), path_in_repo="README.md",
        repo_id=repo, repo_type="dataset")
    log(f"  published: https://huggingface.co/datasets/{repo}")


def _dataset_card(records: list[dict]) -> str:
    by_lang = defaultdict(lambda: {"n": 0, "sec": 0.0})
    emos = defaultdict(int)
    for r in records:
        by_lang[r["language"]]["n"] += 1
        by_lang[r["language"]]["sec"] += r["duration_sec"]
        emos[r["emotion"]] += 1
    total_min = sum(v["sec"] for v in by_lang.values()) / 60.0
    n_clips = len(records)
    lang_rows = "\n".join(
        f"| {config.LANGUAGES[l]['name']} | `{l}` | {by_lang[l]['n']} | {by_lang[l]['sec']/60:.1f} |"
        for l in by_lang)
    emo_rows = "\n".join(f"| `{k}` | {v} |"
                         for k, v in sorted(emos.items(), key=lambda x: -x[1]))
    langs_yaml = "\n".join(f"- {l}" for l in by_lang)
    repo = os.environ.get("HF_DATASET_REPO", "ghostieee11/vaani-speech-corpus")
    sr = config.SAMPLE_RATE // 1000

    return f"""---
license: other
language:
{langs_yaml}
pretty_name: "Vaani: Curated Indian-English + Hindi Speech Corpus"
task_categories:
- text-to-speech
- automatic-speech-recognition
tags:
- tts
- speech
- indian-english
- hindi
- expressive
- emotion
- single-speaker
size_categories:
- n<1K
---

# 🎙️ Vaani: Curated Indian-English + Hindi Speech Corpus

A small, **hand-curated** single-speaker speech corpus (**~{total_min:.0f} minutes**,
**{n_clips} clips**) for expressive Text-to-Speech. Real Indian voices, accurate
transcripts, and emotion tags reviewed by ear.

> Built as a **data-quality and curation exercise**: the pipeline is simple by
> design; the real work is in the listening, correcting, and selecting.

## ✨ Highlights

- 🗣️ **Two real Indian speakers**, one consistent voice per language. No synthetic / AI narration.
- 🎧 **Clean, studio-grade audio** (no background music), verified with VAD and diarization.
- 📝 **Two transcripts per clip**: verbatim and TTS-normalized.
- 🎭 **Emotion / style tags** across {len(config.EMOTIONS)} categories.
- 🔎 **Full provenance**: every clip carries its `source_url` and `license`.

## 📊 Composition

| Language | Code | Clips | Minutes |
|---|---|---|---|
{lang_rows}

| Property | Value |
|---|---|
| Sample rate | **{sr} kHz**, mono, 16-bit WAV |
| Loudness | **{config.TARGET_LUFS:.0f} LUFS** (EBU R128), true-peak ≤ {config.PEAK_CEILING_DBFS:.0f} dBFS |
| Clip length | 4 to 20 s, sentence-bounded |
| Speakers | one voice per language (`speaker_id`) |

## 🗣️ Speakers

| Language | Speaker | Style |
|---|---|---|
| Indian English | **Prof. H.C. Verma** | clear, expressive physics lectures |
| Hindi | **Kahani Suno** | dramatic Premchand literary narration |

## 🎭 Emotion distribution

| Emotion | Clips |
|---|---|
{emo_rows}

## 🧾 Data fields

| Field | Description |
|---|---|
| `audio` | {sr} kHz mono waveform |
| `text` | verbatim transcript (human-corrected) |
| `normalized_text` | TTS-ready (numbers / abbreviations expanded) |
| `language` | `en` or `hi` |
| `speaker_id` | consistent per-language speaker |
| `emotion`, `intensity` | style tag and its intensity |
| `duration_sec`, `snr_db`, `lufs`, `sample_rate` | per-clip audio metrics |
| `source_url`, `license` | provenance |

## 🚀 Usage

```python
from datasets import load_dataset

ds = load_dataset("{repo}", split="train")
ex = ds[0]
print(ex["text"], "|", ex["emotion"])
audio = ex["audio"]   # decoded waveform and sampling rate
```

## 🛠️ How it was built

YouTube audio (yt-dlp) -> ffmpeg standardize ({sr} kHz mono) -> Sarvam
**diarization** single-speaker check -> Silero-VAD segmentation -> Sarvam **ASR**
(`saaras:v3`) drafts -> **human listening, correction and emotion tagging** ->
Sarvam **LLM** text normalization -> automated QC gates (SNR, loudness, peak,
bandwidth, duration). Full pipeline and curation log are in the GitHub repository.

## 📄 Licensing and provenance

Audio is sourced from YouTube for **research and educational use**. Every clip
records its `source_url`, creator and `license`. The sources are under YouTube's
standard license (not Creative Commons); curation prioritised audio quality
(clean, single, real-human Indian voices) over license filtering. This dataset
claims **no ownership** of the source audio and will honour any removal request.

## ⚠️ Limitations

Small corpus, built to demonstrate curation quality rather than scale. Emotion
coverage reflects the chosen speakers (the English physics lectures skew neutral).
Emotion labels are subjective guidance, not ground truth. Not validated for
production training.
"""


# late import so the friendlier "missing file" errors fire first
from pathlib import Path  # noqa: E402

if __name__ == "__main__":
    main()
