# Vaani - Curated Indian-English + Hindi Speech Corpus

A small, **hand-curated** single-speaker text-to-speech corpus (~62 min: ~31 min
Indian English + ~31 min Hindi) sourced from YouTube - real Indian speakers
(**H.C. Verma** physics lectures + **Kahani Suno** Premchand narration) - with
human-verified transcriptions and emotion/style tags.

**📦 Dataset:** https://huggingface.co/datasets/ghostieee11/vaani-speech-corpus

> **This is a data-curation project, not a pipeline demo.** The scripts here are
> deliberately simple. The value is in the judgment: every clip was listened to,
> every transcript human-corrected, every tag confirmed by ear, and every
> keep/cut decision is recorded in [`curation_log.md`](curation_log.md). The
> tools (Sarvam ASR/diarization/LLM, VAD, ffmpeg) **assist**; they do not decide.

## Quality targets (and why)

| Target | Value | Rationale |
|---|---|---|
| Sample rate | 24 kHz mono, 16-bit WAV | Modern neural-TTS standard (LibriTTS-R) |
| Loudness | -23 LUFS, peak ≤ -1 dBFS | EBU R128; consistent level, no clipping |
| SNR | ≥ 25 dB | IndicVoices-R quality bar |
| Effective bandwidth | ≥ 4 kHz | reject telephone-grade band-limiting |
| Clip length | 4-20 s, sentence-bounded | standard TTS range; cut on silence |
| Speakers | 1 voice per language | coherent single-speaker corpus |
| Transcripts | verbatim + normalized | human-corrected from Sarvam ASR drafts |
| Emotion | 8-tag taxonomy, by ear | `neutral, happy, excited, sad, angry, serious, calm, whisper` |
| Sourcing | YouTube, real Indian speakers; provenance logged | quality over CC (documented, research-use) |

All values live in [`src/config.py`](src/config.py).

## Pipeline

```
sources.csv (HUMAN sourcing)
   │  01_download    yt-dlp (+aria2c) acquire YouTube audio
   ▼  02_preprocess  ffmpeg → 24kHz mono 16-bit
   │  03_verify_speaker   Sarvam diarization: confirm single-speaker
   ▼  04_segment     Silero-VAD → 4-15s clips, loudness-normalized
   │  05_transcribe  Sarvam ASR (saaras:v3) → DRAFT transcripts
   ▼  06_prefill_review   Sarvam LLM → normalized-text + emotion SUGGESTIONS
   ┃
   ┣━━ ★ HUMAN: listen to every clip (review.html) and curate review_sheet.csv
   ┃        fix transcripts · confirm emotion by ear · drop bad clips
   ▼  07_qc          audio metrics + gates (SNR/loudness/peak/bandwidth) + figures
   │  08_build_dataset    package + dataset card + push to HuggingFace
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg                      # if not already installed
cp .env.example .env                     # then fill SARVAM_API_KEY + HF_TOKEN
```

## Run

```bash
# after filling in sources.csv:
python src/01_download.py
python src/02_preprocess.py
python src/03_verify_speaker.py          # Sarvam diarization check
python src/04_segment.py
python src/05_transcribe.py              # Sarvam ASR drafts
python src/06_prefill_review.py          # Sarvam LLM suggestions
python src/make_review_html.py           # ★ open review.html, listen, curate review_sheet.csv
python src/07_qc.py                      # QC gates + figures
python src/08_build_dataset.py           # package + (optionally) push to HF
```

## Repo layout

```
src/                 pipeline (01-08) + sarvam_client, utils, config, make_review_html
sources.csv          accepted sources (url, creator, license) - human-curated
curation_log.md      ★ running log of human curation decisions
review_sheet.csv     ★ per-clip human edits (generated, then you curate it)
reports/             qc_report.csv, diarization_report.csv, figures/
report/              the PDF write-up
data/                gitignored: raw, processed, clips, hf_export
```

## Sarvam APIs used

- **ASR** - `speech_to_text.transcribe(model="saaras:v3")` for per-clip drafts.
- **Diarization** - `speech_to_text_job.create_job(with_diarization=True)` to
  confirm sources are single-speaker.
- **LLM** - `chat.completions` for text normalization + emotion suggestions.

All wrapped in [`src/sarvam_client.py`](src/sarvam_client.py) with retries,
backoff, and on-disk response caching (reruns don't re-bill).

## License

Code: MIT. Dataset: research/educational use - audio is YouTube-sourced (not CC);
per-clip `source_url` + `license` provenance in the metadata, no ownership claimed.
