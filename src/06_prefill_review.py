"""06 - Build the human review sheet, pre-filled with machine suggestions.

For each clip we ask the Sarvam LLM for (a) a normalized-text draft (numbers and
abbreviations expanded, punctuation/casing fixed, original script preserved) and
(b) a SUGGESTED emotion. Both are starting points only.

Note: Sarvam LLMs are reasoning models that consume ~2-3k tokens of hidden
reasoning even for trivial asks, so we give them a high token ceiling (4000) and
run the 287 calls through a small thread pool to keep wall-clock reasonable.

Then YOU open review_sheet.csv (and review.html to listen) and:
  * fix `text` to true verbatim, fix `normalized_text`
  * confirm/override `emotion` and `intensity` BY EAR (audio is ground truth;
    text-based emotion suggestions are weak - e.g. a lecture reads as "neutral")
  * set keep = N to drop a clip, with a reason in `notes`

The git diff of your edits to review_sheet.csv is direct evidence of curation.
Safe by default: never overwrites an existing review_sheet.csv.
"""
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from utils import log
import sarvam_client

SYSTEM = (
    "You are a careful TTS data annotator for Indian languages. "
    "Given a short ASR transcript, return STRICT JSON with two keys: "
    "'normalized_text' (the transcript with numbers, dates, currencies and "
    "abbreviations written out in words as a TTS engine should read them, "
    "correct punctuation and casing, SAME language/script as the input, no "
    "translation) and 'emotion' (exactly one of: " + ", ".join(config.EMOTIONS) +
    "). Return only the JSON object."
)


def suggest(asr_text: str, language: str) -> tuple[str, str]:
    if not asr_text:
        return "", "neutral"
    user = f"Language: {config.LANGUAGES[language]['name']}\nTranscript: {asr_text}"
    try:
        raw = sarvam_client.chat(SYSTEM, user, max_tokens=4000)   # reasoning model needs headroom
        start, end = raw.find("{"), raw.rfind("}")
        obj = json.loads(raw[start:end + 1])                      # handles ```json fences
        emo = obj.get("emotion", "neutral").strip().lower()
        if emo not in config.EMOTIONS:
            emo = "neutral"
        return obj.get("normalized_text", asr_text).strip(), emo
    except Exception as e:  # noqa: BLE001
        log(f"  LLM suggestion failed ({type(e).__name__}): keeping verbatim + neutral")
        return asr_text, "neutral"


def main() -> None:
    if config.REVIEW_CSV.exists():
        sys.exit(f"{config.REVIEW_CSV} already exists - refusing to overwrite your "
                 f"edits. Delete it first if you really want to regenerate.")
    if not config.TRANSCRIBED_CSV.exists():
        sys.exit(f"Missing {config.TRANSCRIBED_CSV}. Run 05_transcribe.py first.")

    with open(config.TRANSCRIBED_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    sarvam_client.get_client()   # pre-init shared client before fanning out to threads

    def work(r: dict) -> dict:
        norm, emo = suggest(r["asr_text"], r["language"])
        return {
            "clip_id": r["clip_id"], "language": r["language"],
            "speaker_id": r["speaker_id"], "path": r["path"],
            "duration_sec": r["duration_sec"], "keep": "Y",
            "text": r["asr_text"],          # human corrects to verbatim
            "normalized_text": norm,        # human reviews
            "emotion": emo,                 # human confirms by ear
            "intensity": "medium",
            "asr_text": r["asr_text"],      # read-only, to measure correction rate
            "notes": "",
        }

    out: list = [None] * len(rows)
    done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(work, r): i for i, r in enumerate(rows)}
        for fut in as_completed(futs):
            out[futs[fut]] = fut.result()
            done += 1
            if done % 25 == 0:
                log(f"  prefilled {done}/{len(rows)}")

    fields = ["clip_id", "language", "speaker_id", "path", "duration_sec", "keep",
              "text", "normalized_text", "emotion", "intensity", "asr_text", "notes"]
    with open(config.REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(out)
    log(f"Done. Review sheet -> {config.REVIEW_CSV}")
    log("NEXT (the important part): open review.html, listen, and curate review_sheet.csv.")


if __name__ == "__main__":
    main()
