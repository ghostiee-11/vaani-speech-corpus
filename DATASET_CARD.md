---
license: other
language:
- en
- hi
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

A small, **hand-curated** single-speaker speech corpus (**~62 minutes**,
**285 clips**) for expressive Text-to-Speech. Real Indian voices, accurate
transcripts, and emotion tags reviewed by ear.

> Built as a **data-quality and curation exercise**: the pipeline is simple by
> design; the real work is in the listening, correcting, and selecting.

## ✨ Highlights

- 🗣️ **Two real Indian speakers**, one consistent voice per language. No synthetic / AI narration.
- 🎧 **Clean, studio-grade audio** (no background music), verified with VAD and diarization.
- 📝 **Two transcripts per clip**: verbatim and TTS-normalized.
- 🎭 **Emotion / style tags** across 8 categories.
- 🔎 **Full provenance**: every clip carries its `source_url` and `license`.

## 📊 Composition

| Language | Code | Clips | Minutes |
|---|---|---|---|
| Indian English | `en` | 146 | 30.7 |
| Hindi | `hi` | 139 | 31.6 |

| Property | Value |
|---|---|
| Sample rate | **24 kHz**, mono, 16-bit WAV |
| Loudness | **-23 LUFS** (EBU R128), true-peak ≤ -1 dBFS |
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
| `neutral` | 181 |
| `serious` | 53 |
| `angry` | 23 |
| `sad` | 20 |
| `happy` | 4 |
| `calm` | 3 |
| `excited` | 1 |

## 🧾 Data fields

| Field | Description |
|---|---|
| `audio` | 24 kHz mono waveform |
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

ds = load_dataset("ghostieee11/vaani-speech-corpus", split="train")
ex = ds[0]
print(ex["text"], "|", ex["emotion"])
audio = ex["audio"]   # decoded waveform and sampling rate
```

## 🛠️ How it was built

YouTube audio (yt-dlp) -> ffmpeg standardize (24 kHz mono) -> Sarvam
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
