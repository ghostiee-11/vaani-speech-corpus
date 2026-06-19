"""Generate review.html - a local listening aid for curation.

Opens as a single page with an inline audio player for every clip next to its
draft transcript and suggested emotion, grouped by language. You listen here and
make your keep/fix/tag decisions in review_sheet.csv alongside. Read-only.

Usage:  python src/make_review_html.py   then open review.html in a browser.
"""
import csv
import html
import sys

import config


def rows() -> list[dict]:
    path = config.REVIEW_CSV if config.REVIEW_CSV.exists() else config.TRANSCRIBED_CSV
    if not path.exists():
        sys.exit("Run up to 05_transcribe (or 06_prefill_review) first.")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    data = rows()
    by_lang: dict[str, list[dict]] = {}
    for r in data:
        by_lang.setdefault(r["language"], []).append(r)

    parts = ["""<!doctype html><meta charset="utf-8">
<title>TTS clip review</title>
<style>
 body{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}
 h1{font-size:1.4rem} h2{margin-top:2rem;border-bottom:2px solid #eee;padding-bottom:.3rem}
 .clip{display:grid;grid-template-columns:230px 1fr;gap:1rem;padding:.7rem 0;border-bottom:1px solid #f0f0f0;align-items:center}
 .cid{font-family:monospace;font-size:.8rem;color:#666} audio{width:230px}
 .txt{font-size:1rem} .meta{font-size:.8rem;color:#888;margin-top:.2rem}
 .emo{display:inline-block;background:#eef;border-radius:4px;padding:1px 6px;font-size:.78rem}
</style>
<h1>TTS clip review - listen, then curate <code>review_sheet.csv</code></h1>
<p>Audio is ground truth. Fix transcripts to verbatim, confirm emotion by ear, set <code>keep=N</code> to drop.</p>
"""]
    for lang, items in by_lang.items():
        name = config.LANGUAGES.get(lang, {"name": lang})["name"]
        total = sum(float(r.get("duration_sec", 0) or 0) for r in items) / 60.0
        parts.append(f"<h2>{html.escape(name)} - {len(items)} clips, {total:.1f} min</h2>")
        for r in items:
            text = r.get("text") or r.get("asr_text") or ""
            emo = r.get("emotion", "")
            parts.append(f"""<div class="clip">
 <div><div class="cid">{html.escape(r['clip_id'])}</div>
  <audio controls preload="none" src="{html.escape(r['path'])}"></audio></div>
 <div><div class="txt">{html.escape(text)}</div>
  <div class="meta">{float(r.get('duration_sec',0) or 0):.1f}s · {html.escape(r['speaker_id'])}
   {f'· <span class=emo>{html.escape(emo)}</span>' if emo else ''}</div></div>
</div>""")

    out = config.ROOT / "review.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"[pipeline] wrote {out} ({len(data)} clips). Open it in a browser.")


if __name__ == "__main__":
    main()
