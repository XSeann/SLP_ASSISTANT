
import json
from pathlib import Path
from datetime import datetime

from ipa_char import (
    CONSONANTS,
    VOWELS,
    DIPHTHONGS,
    normalize_phonemes
)

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "soda"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = [
    "Correct",
    "Substitution",
    "Omission",
    "Distortion",
    "Addition"
]


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def split_ipa(text):
    """Split continuous IPA text into individual phonemes."""

    symbols = sorted(
        CONSONANTS | VOWELS | DIPHTHONGS,
        key=len,
        reverse=True
    )

    phonemes = []
    i = 0

    while i < len(text):
        symbol = next(
            (s for s in symbols if text.startswith(s, i)),
            None
        )

        if symbol:
            phonemes.append(symbol)
            i += len(symbol)
        else:
            phonemes.append(text[i])
            i += 1

    return normalize_phonemes(phonemes)


def align_phonemes(target, actual):
    """Levenshtein alignment of target and actual phonemes."""

    rows = len(target) + 1
    cols = len(actual) + 1

    dp = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        dp[i][0] = i

    for j in range(cols):
        dp[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):

            cost = 0 if target[i - 1] == actual[j - 1] else 1

            dp[i][j] = min(
                dp[i - 1][j] + 1,       # Omission
                dp[i][j - 1] + 1,       # Addition
                dp[i - 1][j - 1] + cost # Match/Substitution
            )

    results = []

    i = len(target)
    j = len(actual)

    while i > 0 or j > 0:

        # Match or substitution
        if (
            i > 0 and j > 0
            and dp[i][j] == dp[i - 1][j - 1]
            + (0 if target[i - 1] == actual[j - 1] else 1)
        ):

            category = (
                "Correct"
                if target[i - 1] == actual[j - 1]
                else "Substitution"
            )

            results.append({
                "target": target[i - 1],
                "actual": actual[j - 1],
                "category": category
            })

            i -= 1
            j -= 1

        # Omission
        elif (
            i > 0
            and dp[i][j] == dp[i - 1][j] + 1
        ):

            results.append({
                "target": target[i - 1],
                "actual": None,
                "category": "Omission"
            })

            i -= 1

        # Addition
        else:

            results.append({
                "target": None,
                "actual": actual[j - 1],
                "category": "Addition"
            })

            j -= 1

    return list(reversed(results))


# ============================================================
# DISTORTION CLASSIFICATION
# ============================================================

def apply_distortion_annotations(alignment, annotations, word_index):
    """
    Apply evaluator-confirmed distortion classifications.

    Annotation indexes are zero-based.

    Distortion cannot be reliably determined from IPA strings
    alone, so annotations require an external evaluator.
    """

    for annotation in annotations:

        if annotation.get("word_index") != word_index:
            continue

        target_index = annotation.get("target_index")

        if not isinstance(target_index, int):
            continue

        if target_index < 0:
            continue

        # Locate the corresponding target phoneme
        aligned_index = 0
        for item in alignment:

            if item["target"] is None:
                continue

            if aligned_index == target_index:

                # A distortion must have an actual production
                if item["actual"] is not None:

                    item["category"] = "Distortion"

                break

            aligned_index += 1


# ============================================================
# SODA ANALYSIS
# ============================================================

def soda_main(target_path, actual_path):

    target_path = Path(target_path)
    actual_path = Path(actual_path)

    target_data = load_json(target_path)
    actual_data = load_json(actual_path)

    target_words = target_data.get("words", [])

    # Actual phonemes grouped by word
    actual_groups = actual_data.get(
        "phoneme_words", ""
    ).split()

    # Optional SLP/evaluator annotations
    # Existing phoneme_word JSON remains compatible.
    distortion_annotations = actual_data.get(
        "distortion_annotations", []
    )

    word_results = []

    totals = {
        category: 0
        for category in CATEGORIES
    }

    # --------------------------------------------------------
    # WORD-BY-WORD ANALYSIS
    # --------------------------------------------------------

    for index, target_word in enumerate(target_words):

        word = target_word.get("word", "")

        target_phonemes = normalize_phonemes(
            target_word.get("phonemes", [])
        )

        actual_group = (
            actual_groups[index]
            if index < len(actual_groups)
            else ""
        )

        actual_phonemes = split_ipa(actual_group)

        # Align target and actual phonemes
        alignment = align_phonemes(
            target_phonemes,
            actual_phonemes
        )

        # Apply evaluator-confirmed distortions
        apply_distortion_annotations(
            alignment,
            distortion_annotations,
            index
        )

        # Count classifications for this word
        word_counts = {
            category: sum(
                item["category"] == category
                for item in alignment
            )
            for category in CATEGORIES
        }

        # Update session totals
        for category in CATEGORIES:
            totals[category] += word_counts[category]

        # Preserve original output structure
        word_results.append({

            "word": word,

            "target_phonemes": target_phonemes,

            "actual_phoneme_group": actual_group,

            "actual_phonemes": actual_phonemes,

            "alignment": alignment,

            "counts": word_counts
        })

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    target_count = sum(
        len(normalize_phonemes(
            word.get("phonemes", [])
        ))
        for word in target_words
    )

    report = {

        "module": "SODA Analysis",

        "session": target_data.get(
            "target_input", {}
        ).get(
            "title",
            target_path.stem
        ),

        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),

        "word_results": word_results,

        "summary": {

            **totals,

            "target_phoneme_count": target_count,

            "distortion_note": (
                "Distortions require evaluator-confirmed "
                "annotations or validated acoustic analysis. "
                "Unannotated IPA mismatches are classified "
                "as substitutions."
            ),

            "group_count_matches_target_words": (
                len(actual_groups) == len(target_words)
            )
        }
    }

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    specific_path = OUTPUT_DIR / f"{target_path.stem}.json"

    with open(specific_path, "w", encoding="utf-8") as file:

        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"SODA analysis saved to: {specific_path}")
    print("Summary:", totals)
    print("Target phoneme count:", target_count)

    return specific_path


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    soda_main(
        BASE_DIR / "archive" / "target_phonemes" / "session_1" / "session_1.json",
        BASE_DIR / "phoneme_word" / "session_1.json"
    )
