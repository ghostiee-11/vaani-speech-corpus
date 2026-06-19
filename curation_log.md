# Curation Log

> The human-decision record behind this dataset - what was auditioned, kept, cut,
> and **why**. The PDF report is written from this log. Tools (Sarvam ASR /
> diarization / LLM, Silero-VAD, ffmpeg) assisted; every keep/cut call was a human one.

---

## 1. Brief & sourcing stance

- **Goal:** clean single-speaker segments from YouTube - ~30 min Indian English +
  ~30 min Hindi, one voice per language, emotion/style tags, public HF dataset.
- **Licensing decision:** prioritised **audio quality over strict Creative Commons.**
  Clean, single-voice, non-AI content - especially for *Indian English* - proved
  scarce under a CC-only filter. So: pick the best real-human single voice, **record
  every source's URL + channel + license** in `sources.csv`, and publish with
  attribution + a research-use note. Rationale: the brief explicitly says "source from
  YouTube," and the data-quality bar matters more to the result than the license tag.
  (CC-BY was still preferred where it didn't cost quality.)

## 2. How each candidate was judged (objective checks, then ears)

- **License / metadata:** `yt-dlp --print` → channel, duration, license.
- **Music-bed check:** Silero-VAD splits speech vs pauses; compare RMS. Clean studio
  audio shows a **30-66 dB** speech-vs-pause gap; a music/ambient bed keeps pauses
  loud (**< 18 dB** gap). This caught background scores that aren't obvious at a glance.
- **Single-speaker:** Sarvam **diarization** on a 90 s mid-clip - *and reading the
  diarized transcript*, not just trusting the speaker count (see finding 4.1).
- **Real-vs-AI / accent:** human listen (the decisive check for "Indian English").

## 3. Sources auditioned

| Candidate (id) | Lang | License | Measured | Verdict |
|---|---|---|---|---|
| Neelesh Misra - YKIB `HOh0qn70gXs` | hi | not CC | - | ❌ background music score under narration + non-CC |
| Aaj Ki Kahani (Premchand) `xAMCosCZqUM` +3 | hi | CC-BY | - | ❌ **two narrators** (audition) - breaks one-voice |
| Kahaniyon Ka Safar `JJQHd27q5Ac` | hi | not CC | clean (66 dB) | ➖ clean but a different narrator than the pick |
| **Kahani Suno (Algyojha) `Q1zQpnKyfb4`** | hi | not CC | clean (46 dB), 1 narrator | ✅ **KEPT** - clean, expressive, 48 min one voice |
| English Avenue (graded reader) `Pq2uwssaFRo`,`DuykqNkPgUo` | en | not CC | clean | ❌ likely **AI-narrated / non-Indian** (learn-English channel) |
| Gaur Gopal Das re-upload `8B5-VKk_P9Y` | en | not CC | - | ❌ non-CC re-upload + different voice; official channel = only Shorts |
| Sadhguru 2003 talk `GJk6QqIyUeI` | en | CC-BY | - | ❌ host/questioner present (2 voices) |
| Sadhguru `nuFWniAbkbI` | en | CC-BY | **bed (11.7 dB)**, 1 spk 94% | ❌ single speaker but a **background music bed** |
| **H.C. Verma `bALYnO_HvII`,`woGREVliFsA`** | en | not CC | clean (34-38 dB), 1 prof | ✅ **KEPT** - real Indian-English professor, clean |
| LibriVox Premchand "Do Sakhiyan" (Sonali Ekka) | hi | public-domain | clean, ASR perfect | ⭐ verified-clean fallback (archive.org) |

**Tally:** auditioned ~9 source sets across both languages; kept **1 voice per language**.

## 4. Key findings (report-worthy)

**4.1 Diarization over-splits expressive single narrators.** Both kept sources came
back as "2 speakers" at 72-78% dominant. But *reading* the diarized transcript showed
a single continuous reader: the Hindi narrator voicing **story characters**, and
H.C. Verma's **rhetorical-question teaching** style. Lesson: don't trust the speaker
count - read the data. **Implication for the build:** do NOT auto-drop "second-speaker"
segments; they're the same person.

**4.2 The AI-voice trap.** Many English "story / audiobook / learn-English" channels
(English Avenue, "New Stories Book English", …) use **synthetic narration**. Training a
TTS dataset on TTS output is a silent quality killer. Avoided by choosing a **real,
known Indian speaker** (H.C. Verma) instead of an anonymous "audiobook" channel.

**4.3 Music beds hide in produced talks.** Sadhguru's produced videos and Neelesh
Misra's YKIB carry a background score under the voice (pause gap < 18 dB), which
disqualifies them for clean TTS. **Audiobook narration and lectures were clean** - the
format predicts cleanliness better than the creator's popularity.

## 5. Final sources

- **Hindi - Kahani Suno (`Q1zQpnKyfb4`)** · Premchand *Algyojha* · single male narrator
  · clean (46 dB gap) · expressive (character voices) · `speaker_id = hi_kahanisuno`.
- **English - H.C. Verma (`bALYnO_HvII`, `woGREVliFsA`)** · physics lectures · real
  Indian-English professor · clean (34-38 dB gap) · `speaker_id = en_hcverma`.

## 6. Curation pass - corrections, rejections, tags

Worked review-tool-assisted: a script flags likely-problem clips (QC fails,
speech-density outliers, script-mix, duration extremes) to focus human attention,
and human-directed corrections are applied across all matching clips.

- **Transcript corrections:** the narrator's name **रघु (Raghu)** was mangled by
  ASR into 8 variants (रग्गू ×27, रग्घु ×10, रग्घू ×4, रग्गो ×1, + danda forms).
  Corrected to रघु across **31 clips**. (`asr_text` keeps the originals, so the
  correction is auditable in the data itself.)
- **Rejections:** `en_02_044` dropped - 14.2 s for 19 characters (1.3 ch/s): an
  incomplete fragment with dead air. `en_02_021`, `en_02_023` flagged for a
  human spot-check (short phrases + long pauses).
- **Emotion:** LLM-suggested from transcript (Hindi varied - serious/sad/angry/
  neutral matching the dramatic story; English correctly mostly-neutral for a
  lecture). These are text-derived starting points; ear-verification is the next
  refinement for a production set.

## 7. Findings & iterations (before → after)

Pipeline iterations forced by listening/looking at the data:

1. **QC bandwidth gate failed 100% of clips.** Root cause: "frequency holding
   99.5% of energy" reads ~3 kHz for *any* speech (energy concentrates low).
   Replaced with an HF-edge band-limit detector → realistic 4-10 kHz, 286/287 pass.
2. **LLM returned empty for every clip.** Sarvam is a reasoning model that burns
   ~2-3k tokens of hidden reasoning before answering; at 400 tokens it never
   emitted JSON. Raised ceiling to 4000 + parallelised → real emotion labels.
3. **Diarization "2 speakers" was a single narrator.** Verified by *reading* the
   diarized transcript (character voices), so we don't auto-drop "speaker 2".
4. **Speech-density flags are script-relative.** Hindi (Devanagari) runs ~9-10
   ch/s vs English ~7-8; absolute thresholds mislabel Hindi - flag within-language.
5. **H.C. Verma's demonstration pauses** produce low-speech English clips (he
   rotates bulbs / shows shadows mid-sentence) - mostly valid, a few dropped.

## 8. What I'd do with more time

- Second annotator + inter-annotator agreement on emotion.
- Forced alignment (WhisperX/MFA) on GPU for word-level timing.
- Broaden expressive range (lectures skew neutral/explanatory); add more of the
  Hindi narrator's dialogue-heavy passages for emotion diversity.
