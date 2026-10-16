import json
from pathlib import Path
from datetime import datetime

from ipa_char import CONSONANTS, VOWELS, DIPHTHONGS, normalize_phonemes

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "soda"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def split_ipa(text):
    """Split a word's IPA string using the reference IPA inventory."""

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
    """Levenshtein alignment of target and actual phoneme sequences."""
    rows, cols = len(target) + 1, len(actual) + 1
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
                dp[i - 1][j - 1] + cost # Match/substitution
            )

    results = []
    i, j = len(target), len(actual)

    while i > 0 or j > 0:
        if (
            i > 0 and j > 0
            and dp[i][j] == dp[i - 1][j - 1]
            + (0 if target[i - 1] == actual[j - 1] else 1)
        ):
            if target[i - 1] == actual[j - 1]:
                category = "Correct"
            else:
                category = "Substitution"

            results.append({
                "target": target[i - 1],
                "actual": actual[j - 1],
                "category": category
            })
            i -= 1
            j -= 1

        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            results.append({
                "target": target[i - 1],
                "actual": None,
                "category": "Omission"
            })
            i -= 1

        else:
            results.append({
                "target": None,
                "actual": actual[j - 1],
                "category": "Addition"
            })
            j -= 1

    return list(reversed(results))


# ============================================================
# SODA ANALYSIS
# ============================================================

def soda_main(target_path, actual_path):
    target_data = load_json(target_path)
    actual_data = load_json(actual_path)

    target_words = target_data.get("words", [])
    actual_groups = actual_data.get("phoneme_words", "").split()

    word_results = []
    totals = {
        "Correct": 0,
        "Substitution": 0,
        "Omission": 0,
        "Distortion": 0,
        "Addition": 0
    }

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

        alignment = align_phonemes(target_phonemes, actual_phonemes)

        for item in alignment:
            totals[item["category"]] += 1

        word_results.append({
            "word": word,
            "target_phonemes": target_phonemes,
            "actual_phoneme_group": actual_group,
            "actual_phonemes": actual_phonemes,
            "alignment": alignment,
            "counts": {
                category: sum(
                    item["category"] == category for item in alignment
                )
                for category in totals
            }
        })

    target_count = sum(len(w.get("phonemes", [])) for w in target_words)

    report = {
        "module": "SODA Analysis",
        "session": target_data.get("target_input", {}).get("title", target_path.stem),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "word_results": word_results,
        "summary": {
            **totals,
            "target_phoneme_count": target_count,
            "distortion_note": (
                "Distortions cannot be reliably identified from phoneme "
                "strings alone; audio review or phonetic judgment is needed."
            ),
            "group_count_matches_target_words": (
                len(actual_groups) == len(target_words)
            )
        }
    }

    specific_path = OUTPUT_DIR / f"{target_path.stem}.json"

    with open(specific_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print(f"SODA analysis saved to: {specific_path}")
    print("Summary:", totals)

    return specific_path

if __name__ == "__main__":
    soda_main(BASE_DIR / "target_phonemes" / "session_1" / "session_1.json", 
              BASE_DIR / "phoneme_word" / "session_1.json")