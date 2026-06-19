"""Shared helpers: env loading, audio I/O, and the QC measurements that back
every quality gate in config.py. Kept dependency-light; heavy libs (librosa)
are imported lazily inside the functions that use them.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv optional at import time
    load_dotenv = None


# --------------------------------------------------------------------- env
def load_env() -> None:
    """Load .env from the repo root (if python-dotenv is installed)."""
    if load_dotenv is not None:
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"ERROR: environment variable {name} is not set (see .env.example)")
    return val


# --------------------------------------------------------------------- logging
def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


# --------------------------------------------------------------------- audio I/O
def read_audio(path) -> tuple[np.ndarray, int]:
    """Return (float32 mono samples in [-1, 1], sample_rate)."""
    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim > 1:               # downmix to mono
        audio = audio.mean(axis=1)
    return audio, sr


def write_audio(path, audio: np.ndarray, sr: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr, subtype="PCM_16")


def duration_sec(audio: np.ndarray, sr: int) -> float:
    return len(audio) / float(sr)


# --------------------------------------------------------------------- loudness
def measure_lufs(audio: np.ndarray, sr: int) -> float:
    import pyloudnorm as pyln
    meter = pyln.Meter(sr)                     # EBU R128 / ITU-R BS.1770
    return float(meter.integrated_loudness(audio))


def normalize_lufs(audio: np.ndarray, sr: int, target_lufs: float,
                   peak_ceiling_dbfs: float) -> np.ndarray:
    """Loudness-normalize to target LUFS, then guarantee a true-peak ceiling."""
    import pyloudnorm as pyln
    loudness = pyln.Meter(sr).integrated_loudness(audio)
    if np.isfinite(loudness):
        audio = pyln.normalize.loudness(audio, loudness, target_lufs)
    # hard ceiling so nothing clips
    peak = np.max(np.abs(audio)) + 1e-9
    ceiling = 10 ** (peak_ceiling_dbfs / 20.0)
    if peak > ceiling:
        audio = audio * (ceiling / peak)
    return audio.astype(np.float32)


def peak_dbfs(audio: np.ndarray) -> float:
    peak = float(np.max(np.abs(audio))) + 1e-12
    return 20.0 * np.log10(peak)


# --------------------------------------------------------------------- SNR
def estimate_snr_db(audio: np.ndarray, sr: int, frame_ms: float = 20.0) -> float:
    """Quick VAD-free SNR estimate: ratio of speech-frame energy (high
    percentile) to noise-floor energy (low percentile). Good enough to *rank*
    and *gate* clips; not a calibrated absolute measurement (documented).
    """
    frame = max(1, int(sr * frame_ms / 1000.0))
    n = len(audio) // frame
    if n < 4:
        return float("nan")
    frames = audio[: n * frame].reshape(n, frame)
    energy = np.mean(frames ** 2, axis=1) + 1e-12
    noise = np.percentile(energy, 10)          # quietest 10% ≈ noise floor
    signal = np.percentile(energy, 90)         # loudest 10% ≈ speech
    return float(10.0 * np.log10(signal / noise))


# --------------------------------------------------------------------- bandwidth
def effective_bandwidth_hz(audio: np.ndarray, sr: int, margin_db: float = 12.0) -> float:
    """Highest frequency carrying real signal energy above the HF noise floor -
    a band-limit detector for telephone/upsampled audio.

    NOTE: an energy-percentile 'rolloff' is unsuitable here - speech energy
    concentrates below ~4 kHz even in full-band audio, so that method
    under-reports bandwidth and flags every clip. Instead we find where the
    frame-averaged spectrum drops to the near-Nyquist noise floor.
    """
    n = 2048
    if len(audio) < n:
        return 0.0
    win = np.hanning(n)
    step = n // 2
    power = np.mean(
        [np.abs(np.fft.rfft(audio[i:i + n] * win)) ** 2
         for i in range(0, len(audio) - n, step)], axis=0)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    pdb = 10.0 * np.log10(power + 1e-12)
    floor = np.median(pdb[int(len(pdb) * 0.9):])     # noise floor near Nyquist
    above = np.where(pdb >= floor + margin_db)[0]
    return float(freqs[above[-1]]) if len(above) else 0.0
