"""
Central configuration for the TTS dataset curation pipeline.

Every quality decision lives here so the report can cite a single source of
truth, and so reviewers can see the targets at a glance. Values are justified
in README.md (Quality Targets) and report/.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"                 # downloaded source audio (gitignored)
PROCESSED = DATA / "processed"     # standardized full-length WAVs (gitignored)
CLIPS = DATA / "clips"             # final segmented clips, per language (gitignored)
JOBS = DATA / "sarvam_jobs"        # Sarvam batch-job outputs (diarization)
CACHE = ROOT / ".cache"            # cached API responses (avoid re-billing)
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

SOURCES_CSV = ROOT / "sources.csv"
SEGMENTS_CSV = DATA / "segments.csv"        # produced by 04_segment
TRANSCRIBED_CSV = DATA / "transcribed.csv"  # produced by 05_transcribe
REVIEW_CSV = ROOT / "review_sheet.csv"      # HUMAN edits this (the core step)
QC_CSV = REPORTS / "qc_report.csv"          # produced by 07_qc

# ---------------------------------------------------------------- languages / speakers
# One consistent voice per language (decision). speaker_id is assigned per source
# in sources.csv; we expect exactly one speaker_id per language in the final set.
LANGUAGES = {
    "en": {"name": "Indian English", "sarvam_code": "en-IN", "target_minutes": 30},
    "hi": {"name": "Hindi",          "sarvam_code": "hi-IN", "target_minutes": 30},
}

# ---------------------------------------------------------------- audio targets
SAMPLE_RATE = 24_000      # Hz, mono - modern neural-TTS standard (LibriTTS-R)
CHANNELS = 1
SAMPLE_WIDTH = 16         # bit
TARGET_LUFS = -23.0       # EBU R128 integrated loudness
PEAK_CEILING_DBFS = -1.0  # true-peak ceiling after normalization (no clipping)
MIN_SNR_DB = 25.0         # reject clips below this (IndicVoices-R bar)
MIN_BANDWIDTH_HZ = 4_000  # HF edge below this ≈ telephone-grade band-limiting

# ---------------------------------------------------------------- segmentation
CLIP_MIN_SEC = 4.0
CLIP_MAX_SEC = 15.0
CLIP_HARD_MAX_SEC = 20.0  # absolute ceiling before forced split
VAD_MIN_SILENCE_SEC = 0.40   # split only on pauses >= this (≈ sentence boundary)
EDGE_PAD_SEC = 0.15          # silence padding kept at clip edges

# ---------------------------------------------------------------- Sarvam models
#   Verify against dashboard.sarvam.ai if a call 404s - names evolve.
ASR_MODEL_REALTIME = "saaras:v3"    # per-clip transcription (<30s audio)
ASR_MODEL_BATCH = "saarika:v2.5"    # batch job for diarization on full sources
LLM_MODEL = "sarvam-30b"            # normalization + emotion suggestion (sarvam-m deprecated)

# ---------------------------------------------------------------- emotion taxonomy
# Compact, defined set. Definitions are published in the dataset card.
EMOTIONS = [
    "neutral", "happy", "excited", "sad",
    "angry", "serious", "calm", "whisper",
]
INTENSITIES = ["low", "medium", "high"]

# ---------------------------------------------------------------- publishing
DATASET_LICENSE = "other"   # YouTube-sourced; research/educational use, per-clip provenance logged
