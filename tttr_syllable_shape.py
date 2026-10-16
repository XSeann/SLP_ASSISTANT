import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

from ipa_char import VOWELS, DIPHTHONGS, normalize_phonemes

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "tttr_syllable_shape"
OUTPUT_FILE.mkdir(parents=True, exist_ok=True)

# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def clean_word(word):
    return re.sub(r"[^\w'-]", "", word).lower().strip()


def templin_ttr(words):
    words = [clean_word(w) for w in words if clean_word(w)]
    counts = Counter(words)
    total = len(words)
    types = len(counts)

    return {
        "types": types,
        "tokens": total,
        "TTR": round(types / total * 100, 2) if total else 0,
        "unique_words": sorted(counts.keys())
    }


def get_word_phoneme_groups(actual):
    """Read phoneme_words, which contains space-separated word groups."""
    text = actual.get("phoneme_words", "").strip()
    return [group for group in text.split() if group]


def split_phonemes(group):
    """Split an IPA string into known multi-character and single symbols."""
    symbols = sorted(
        set(VOWELS) | set(DIPHTHONGS),
        key=len,
        reverse=True
    )

    phonemes = []
    i = 0

    while i < len(group):
        match = next(
            (symbol for symbol in symbols if group.startswith(symbol, i)),
            None
        )

        if match:
            phonemes.append(match)
            i += len(match)
        else:
            # Keep an unrecognized character rather than silently dropping it.
            phonemes.append(group[i])
            i += 1

    return normalize_phonemes(phonemes)


def sound_type(phoneme):
    if phoneme in VOWELS or phoneme in DIPHTHONGS:
        return "V"
    return "C"


# ============================================================
# SYLLABLE SHAPE
# ============================================================

def syllable_shapes(phonemes):
    if not phonemes:
        return {"syllable_count": 0, "shapes": []}

    nuclei = [i for i, p in enumerate(phonemes) if sound_type(p) == "V"]

    if not nuclei:
        return {"syllable_count": 0, "shapes": []}

    # Divide consonants between adjacent vowel nuclei.
    boundaries = [0]
    for left, right in zip(nuclei, nuclei[1:]):
        boundary = right if right - left <= 2 else right - 1
        boundaries.append(boundary)
    boundaries.append(len(phonemes))

    shapes = []
    for i in range(len(boundaries) - 1):
        chunk = phonemes[boundaries[i]:boundaries[i + 1]]
        shapes.append("".join(sound_type(p) for p in chunk))

    return {"syllable_count": len(nuclei), "shapes": shapes}


# ============================================================
# WORD-LEVEL ANALYSIS
# ============================================================

def analyze_words(transcript, phoneme_groups):
    segments = transcript.get("segments", [])
    results = []

    for index, segment in enumerate(segments):
        word = clean_word(segment.get("word", ""))
        if not word:
            continue

        group = (
            phoneme_groups[index]
            if index < len(phoneme_groups)
            else ""
        )

        phonemes = split_phonemes(group)
        analysis = syllable_shapes(phonemes)

        results.append({
            "word": word,
            "start": segment.get("start", 0),
            "end": segment.get("end", 0),
            "phoneme_group": group,
            "phonemes": phonemes,
            "syllable_count": analysis["syllable_count"],
            "syllable_shapes": analysis["shapes"]
        })

    return results


def summarize_shapes(word_results):
    counts = Counter(
        shape
        for word in word_results
        for shape in word["syllable_shapes"]
    )
    total = sum(counts.values())

    return {
        "total_syllables": total,
        "shape_counts": dict(sorted(counts.items())),
        "shape_percentages": {
            shape: round(count / total * 100, 2)
            for shape, count in sorted(counts.items())
        } if total else {}
    }


# ============================================================
# MAIN
# ============================================================

def templin_ttr_syllable_main(actual_path, transcript_path):
    actual = load_json(actual_path)
    transcript = load_json(transcript_path)

    words = [
        segment.get("word", "")
        for segment in transcript.get("segments", [])
    ]

    ttr = templin_ttr(words)
    phoneme_groups = get_word_phoneme_groups(actual)
    actual_words = analyze_words(transcript, phoneme_groups)
    shape_summary = summarize_shapes(actual_words)

    report = {
        "module": "TEMPLIN TTR and Syllable Shape Analysis",
        "session": transcript_path.stem,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "TEMPLIN_TTR": ttr,
        "actual_syllable_analysis": actual_words,
        "actual_syllable_shapes": shape_summary,
        "notes": [
            "TTR is calculated from transcript words.",
            "Syllable shapes use the word-grouped phoneme_words field.",
            "Phoneme groups are paired with transcript words in order.",
            "Syllable shapes are heuristic estimates, not clinical measurements.",
            "The phoneme group count should match the transcript word count."
        ]
    }

    specific_path = Path(OUTPUT_FILE / f"{transcript_path.stem}.json")

    with open(specific_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print(f"Analysis saved to: {specific_path}")
    print(f"TTR: {ttr['TTR']}%")
    print(f"Total syllables estimated: {shape_summary['total_syllables']}")

    return specific_path

if __name__ == "__main__":
    templin_ttr_syllable_main(
        BASE_DIR / "phoneme_word" / "session_1.json",
        BASE_DIR / "transcription" / "session_1.json"
    )