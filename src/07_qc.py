"""07 - Automated QC gates + figures, on the clips you chose to keep.

Computes per-clip duration, loudness (LUFS), true-peak, SNR estimate, effective
bandwidth, and sample rate, then flags each against the targets in config.py.
The gates are advisory: a FAIL means "listen again / probably drop", not an
automatic delete - you keep final say. Produces reports/qc_report.csv and the
figures used in the PDF report.
"""
import csv
import sys

import config
from utils import (log, read_audio, duration_sec, measure_lufs, peak_dbfs,
                   estimate_snr_db, effective_bandwidth_hz)


def kept_rows() -> list[dict]:
    if not config.REVIEW_CSV.exists():
        sys.exit(f"Missing {config.REVIEW_CSV}. Run 06_prefill_review.py and curate it.")
    with open(config.REVIEW_CSV, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if (r.get("keep") or "").strip().upper() == "Y"]


def main() -> None:
    rows = kept_rows()
    if not rows:
        sys.exit("No kept clips (keep=Y) in review_sheet.csv yet.")

    out = []
    for i, r in enumerate(rows, 1):
        audio, sr = read_audio(config.ROOT / r["path"])
        dur = duration_sec(audio, sr)
        lufs = measure_lufs(audio, sr)
        peak = peak_dbfs(audio)
        snr = estimate_snr_db(audio, sr)
        bw = effective_bandwidth_hz(audio, sr)
        fails = []
        if not (config.CLIP_MIN_SEC - 0.5 <= dur <= config.CLIP_HARD_MAX_SEC + 0.5):
            fails.append("duration")
        if snr == snr and snr < config.MIN_SNR_DB:        # NaN-safe
            fails.append("snr")
        if peak > config.PEAK_CEILING_DBFS + 0.5:
            fails.append("clipping")
        if bw < config.MIN_BANDWIDTH_HZ:
            fails.append("bandwidth")
        if abs(lufs - config.TARGET_LUFS) > 2.0:
            fails.append("loudness")
        out.append({
            "clip_id": r["clip_id"], "language": r["language"], "emotion": r["emotion"],
            "duration_sec": f"{dur:.2f}", "lufs": f"{lufs:.1f}", "peak_dbfs": f"{peak:.1f}",
            "snr_db": f"{snr:.1f}", "bandwidth_hz": f"{bw:.0f}", "sample_rate": sr,
            "qc_pass": "Y" if not fails else "N", "flags": ";".join(fails),
        })
        if i % 25 == 0:
            log(f"  QC {i}/{len(rows)}")

    config.QC_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(config.QC_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    _figures(out)
    _summary(out)
    log(f"Done. QC report -> {config.QC_CSV}; figures -> {config.FIGURES}")


def _summary(out: list[dict]) -> None:
    passed = [r for r in out if r["qc_pass"] == "Y"]
    log(f"  clips kept={len(out)}  QC-pass={len(passed)} ({len(passed)/len(out):.0%})")
    for lang in config.LANGUAGES:
        mins = sum(float(r["duration_sec"]) for r in passed if r["language"] == lang) / 60.0
        n = sum(1 for r in passed if r["language"] == lang)
        log(f"  {lang}: {n} clips, {mins:.1f} min (target {config.LANGUAGES[lang]['target_minutes']})")


def _figures(out: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        log(f"  matplotlib unavailable, skipping figures: {e}"); return
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    passed = [r for r in out if r["qc_pass"] == "Y"]

    def save(fig, name):
        fig.tight_layout(); fig.savefig(config.FIGURES / name, dpi=130); plt.close(fig)

    durs = [float(r["duration_sec"]) for r in passed]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.hist(durs, bins=20, color="#3b7dd8", edgecolor="white")
    ax.set(title="Clip duration distribution", xlabel="seconds", ylabel="clips")
    save(fig, "duration_hist.png")

    snrs = [float(r["snr_db"]) for r in passed if r["snr_db"] not in ("nan", "")]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.hist(snrs, bins=20, color="#2e9e7b", edgecolor="white")
    ax.axvline(config.MIN_SNR_DB, color="crimson", ls="--", label=f"min {config.MIN_SNR_DB} dB")
    ax.set(title="SNR estimate", xlabel="dB", ylabel="clips"); ax.legend()
    save(fig, "snr_hist.png")

    emos = {}
    for r in passed:
        emos[r["emotion"]] = emos.get(r["emotion"], 0) + 1
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.bar(list(emos.keys()), list(emos.values()), color="#d8843b")
    ax.set(title="Emotion / style distribution", ylabel="clips")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    save(fig, "emotion_counts.png")

    langs = list(config.LANGUAGES)
    mins = [sum(float(r["duration_sec"]) for r in passed if r["language"] == l) / 60 for l in langs]
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.bar([config.LANGUAGES[l]["name"] for l in langs], mins, color="#8b5cf6")
    ax.axhline(30, color="gray", ls="--", label="30 min target")
    ax.set(title="Minutes per language", ylabel="minutes"); ax.legend()
    save(fig, "minutes_per_language.png")


if __name__ == "__main__":
    main()
