"""04 - Segment each standardized source into TTS-ready clips.

Uses Silero-VAD to find speech regions separated by natural pauses (>= 400 ms,
which align with sentence boundaries ~95% of the time), then greedily packs
consecutive speech regions into 4-15 s clips WITHOUT cutting mid-word. Each clip
is loudness-normalized to the target LUFS with a true-peak ceiling.

Output: data/clips/<lang>/<source_id>_NNN.wav  + data/segments.csv
You then listen to these clips and curate them (the real work).
"""
import csv
import sys

import numpy as np

import config
from utils import log, read_audio, write_audio, normalize_lufs


def source_meta() -> dict[str, dict]:
    meta = {}
    if config.SOURCES_CSV.exists():
        with open(config.SOURCES_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                sid = (r.get("source_id") or "").strip()
                if sid and not sid.startswith("#"):
                    meta[sid] = {"language": (r.get("language") or "en").strip(),
                                 "speaker_id": (r.get("speaker_id") or sid).strip()}
    return meta


def speech_regions(audio: np.ndarray, sr: int) -> list[tuple[float, float]]:
    import torch
    import librosa
    from silero_vad import load_silero_vad, get_speech_timestamps
    model = load_silero_vad()
    wav16 = librosa.resample(audio, orig_sr=sr, target_sr=16000) if sr != 16000 else audio
    ts = get_speech_timestamps(
        torch.from_numpy(wav16.astype(np.float32)), model,
        sampling_rate=16000,
        min_silence_duration_ms=int(config.VAD_MIN_SILENCE_SEC * 1000),
        min_speech_duration_ms=200,
        return_seconds=True,
    )
    return [(float(t["start"]), float(t["end"])) for t in ts]


def pack_clips(regions: list[tuple[float, float]]) -> list[tuple[float, float]]:
    clips, cur = [], None
    for start, end in regions:
        if cur is None:
            cur = [start, end]
        elif end - cur[0] <= config.CLIP_MAX_SEC:
            cur[1] = end
        else:
            if cur[1] - cur[0] >= config.CLIP_MIN_SEC:
                clips.append(tuple(cur)); cur = [start, end]
            else:                               # current too short - extend anyway
                cur[1] = end
                if cur[1] - cur[0] >= config.CLIP_MIN_SEC:
                    clips.append(tuple(cur)); cur = None
    if cur is not None and cur[1] - cur[0] >= config.CLIP_MIN_SEC:
        clips.append(tuple(cur))

    # force-split any clip longer than the hard ceiling
    out = []
    for s, e in clips:
        if e - s <= config.CLIP_HARD_MAX_SEC:
            out.append((s, e)); continue
        n = int(np.ceil((e - s) / config.CLIP_MAX_SEC))
        step = (e - s) / n
        out.extend((s + i * step, s + (i + 1) * step) for i in range(n))
    return out


def main() -> None:
    meta = source_meta()
    sources = sorted(config.PROCESSED.glob("*.wav"))
    if not sources:
        sys.exit(f"No processed audio in {config.PROCESSED}. Run 02_preprocess.py first.")

    rows = []
    for src in sources:
        m = meta.get(src.stem, {"language": "en", "speaker_id": src.stem})
        lang = m["language"]
        audio, sr = read_audio(src)
        regions = speech_regions(audio, sr)
        clips = pack_clips(regions)
        out_dir = config.CLIPS / lang
        out_dir.mkdir(parents=True, exist_ok=True)
        log(f"{src.stem} [{lang}]: {len(regions)} speech regions -> {len(clips)} clips")

        for i, (start, end) in enumerate(clips):
            a = max(0, int((start - config.EDGE_PAD_SEC) * sr))
            b = min(len(audio), int((end + config.EDGE_PAD_SEC) * sr))
            clip = normalize_lufs(audio[a:b], sr, config.TARGET_LUFS, config.PEAK_CEILING_DBFS)
            clip_id = f"{src.stem}_{i:03d}"
            path = out_dir / f"{clip_id}.wav"
            write_audio(path, clip, sr)
            rows.append({
                "clip_id": clip_id, "language": lang, "source_id": src.stem,
                "speaker_id": m["speaker_id"], "path": str(path.relative_to(config.ROOT)),
                "start_sec": f"{start:.2f}", "end_sec": f"{end:.2f}",
                "duration_sec": f"{(b - a) / sr:.2f}",
            })

    config.SEGMENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SEGMENTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["clip_id", "language", "source_id", "speaker_id",
                                          "path", "start_sec", "end_sec", "duration_sec"])
        w.writeheader(); w.writerows(rows)

    total_min = sum(float(r["duration_sec"]) for r in rows) / 60.0
    log(f"Done. {len(rows)} clips ({total_min:.1f} min) -> {config.SEGMENTS_CSV}")


if __name__ == "__main__":
    main()
