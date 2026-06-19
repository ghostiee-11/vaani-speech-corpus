"""Thin wrapper around the Sarvam SDK.

Responsibilities:
  * single place to construct the client (auth from .env)
  * retries with exponential backoff on transient errors / rate limits
  * on-disk caching of responses (keyed by input hash) so reruns are free and
    the pipeline is reproducible without re-billing.

All three Sarvam capabilities the assignment asks for are here:
  - ASR  : transcribe_clip()        (real-time, per <30s clip)
  - LLM  : chat()                   (text normalization + emotion suggestion)
  - Diarization : diarize_source()  (batch job on full-length source audio)
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path

from sarvamai import SarvamAI

import config
from utils import load_env, require_env, log


# --------------------------------------------------------------------- client
_CLIENT: SarvamAI | None = None


def get_client() -> SarvamAI:
    global _CLIENT
    if _CLIENT is None:
        load_env()
        _CLIENT = SarvamAI(api_subscription_key=require_env("SARVAM_API_KEY"))
    return _CLIENT


# --------------------------------------------------------------------- cache
def _cache_path(kind: str, key: str) -> Path:
    config.CACHE.mkdir(parents=True, exist_ok=True)
    return config.CACHE / f"{kind}_{key}.json"


def _file_hash(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _retry(fn, *, tries: int = 5, base: float = 2.0):
    """Call fn() with exponential backoff. Returns fn() or raises last error."""
    last = None
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - SDK raises varied exception types
            last = e
            wait = base ** attempt
            log(f"  API error ({type(e).__name__}): {e} - retry in {wait:.0f}s")
            time.sleep(wait)
    raise last


# --------------------------------------------------------------------- ASR (per clip)
def transcribe_clip(audio_path, language_code: str) -> dict:
    """Transcribe one short (<30s) clip. Returns {'transcript', 'language_code'}.
    Cached on (file content, model, language)."""
    key = f"{_file_hash(audio_path)}_{config.ASR_MODEL_REALTIME}_{language_code}".replace(":", "")
    cache = _cache_path("asr", key)
    if cache.exists():
        return json.loads(cache.read_text())

    def _call():
        with open(audio_path, "rb") as fh:
            return get_client().speech_to_text.transcribe(
                file=fh,
                model=config.ASR_MODEL_REALTIME,
                language_code=language_code,
            )

    resp = _retry(_call)
    out = {
        "transcript": getattr(resp, "transcript", "") or "",
        "language_code": getattr(resp, "language_code", language_code),
    }
    cache.write_text(json.dumps(out, ensure_ascii=False))
    return out


# --------------------------------------------------------------------- LLM
def chat(system: str, user: str, *, temperature: float = 0.1, max_tokens: int = 800,
         reasoning_effort: str = "low") -> str:
    """One-shot chat completion. Cached on (system+user, model).

    Sarvam LLMs are reasoning models: without `reasoning_effort="low"` the chain
    of thought consumes the token budget and `message.content` comes back None.
    """
    key = _text_hash(f"{config.LLM_MODEL}|{reasoning_effort}|{max_tokens}|{system}|{user}")
    cache = _cache_path("llm", key)
    if cache.exists():
        return json.loads(cache.read_text())["content"]

    def _call():
        return get_client().chat.completions(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )

    resp = _retry(_call)
    try:
        content = resp.choices[0].message.content
    except Exception:
        content = None
    if not content:                     # truncated reasoning / empty completion
        content = ""
    cache.write_text(json.dumps({"content": content}, ensure_ascii=False))
    return content


# --------------------------------------------------------------------- Diarization (batch)
def diarize_source(audio_path, language_code: str, num_speakers: int = 1,
                   out_dir: Path | None = None) -> Path:
    """Run a Sarvam batch STT job WITH diarization on a full-length source file
    to verify it is single-speaker (and locate any second-speaker bleed).
    Returns the directory holding the downloaded job output JSON.
    Skips the (billable) job if output already exists.
    """
    out_dir = Path(out_dir or (config.JOBS / Path(audio_path).stem))
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.glob("*.json")):
        log(f"  diarization cached for {Path(audio_path).name}")
        return out_dir

    def _call():
        client = get_client()
        job = client.speech_to_text_job.create_job(
            model=config.ASR_MODEL_BATCH,
            with_diarization=True,
            with_timestamps=True,
            language_code=language_code,
            num_speakers=max(1, num_speakers),
        )
        job.upload_files(file_paths=[str(audio_path)], timeout=180.0)
        job.start()
        job.wait_until_complete(poll_interval=10, timeout=1800)
        if job.is_failed():
            raise RuntimeError(f"diarization job failed for {audio_path}")
        job.download_outputs(output_dir=str(out_dir))
        return out_dir

    return _retry(_call, tries=3)
