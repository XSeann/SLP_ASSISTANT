
import json
from pathlib import Path
from datetime import datetime

from ipa_char import (
    CONSONANTS,
    VOWELS,
    DIPHTHONGS,
    normalize_phonemes,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "pcc_pvc"
OUTPUT_FILE.mkdir(parents=True, exist_ok=True)

def load_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def get_target_phonemes(data):
    """Read target phonemes from the target word JSON."""
    phonemes = []

    for word in data.get("words", []):
        phonemes.extend(word.get("phonemes", []))

    return normalize_phonemes(phonemes)


def get_actual_phonemes(data):
    """Read actual phonemes from supported JSON structures."""
    records = data.get("phonemes", [])

    if records:
        phonemes = [
            item if isinstance(item, str) else item.get("phoneme", "")
            for item in records
        ]
        phonemes = [p for p in phonemes if p]
    else:
        sequence = data.get("phoneme_sequence", "")
        phonemes = sequence.split() if sequence else []

    return normalize_phonemes(phonemes)


def classify(phoneme):
    """Classify a phoneme for PCC/PVC calculation."""
    if phoneme in CONSONANTS:
        return "consonant"
    if phoneme in VOWELS or phoneme in DIPHTHONGS:
        return "vowel"
    return "unclassified"


def align_phonemes(target, actual):
    """Levenshtein alignment with backtracking."""
    n, m = len(target), len(actual)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if target[i - 1] == actual[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # Deletion
                dp[i][j - 1] + 1,       # Insertion
                dp[i - 1][j - 1] + cost # Match/substitution
            )

    aligned = []
    i, j = n, m

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if target[i - 1] == actual[j - 1] else 1

            if dp[i][j] == dp[i - 1][j - 1] + cost:
                aligned.append({
                    "target": target[i - 1],
                    "actual": actual[j - 1],
                    "result": "correct" if cost == 0 else "substitution"
                })
                i -= 1
                j -= 1
                continue

        if i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            aligned.append({
                "target": target[i - 1],
                "actual": None,
                "result": "omission"
            })
            i -= 1
        else:
            aligned.append({
                "target": None,
                "actual": actual[j - 1],
                "result": "insertion"
            })
            j -= 1

    return list(reversed(aligned))


def calculate_pcc_pvc(target, actual):
    aligned = align_phonemes(target, actual)

    results = {}

    for sound_type in ("consonant", "vowel"):
        target_count = sum(
            classify(p) == sound_type for p in target
        )

        correct_count = sum(
            item["result"] == "correct"
            and item["target"] is not None
            and classify(item["target"]) == sound_type
            for item in aligned
        )

        results[sound_type] = {
            "correct": correct_count,
            "total": target_count,
            "percentage": round(
                correct_count / target_count * 100, 2
            ) if target_count else None
        }

    return results, aligned


def pcc_pvc_main(target_path, actual_path):
    target_data = load_json(target_path)
    actual_data = load_json(actual_path)

    target = get_target_phonemes(target_data)
    actual = get_actual_phonemes(actual_data)

    scores, alignment = calculate_pcc_pvc(target, actual)

    report = {
        "module": "PCC and PVC Analysis",
        "session": target_data.get("target_input", {}).get(
            "title", "Unknown session"
        ),
        "sentence": target_data.get("target_input", {}).get(
            "sentence", ""
        ),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "target_phonemes": target,
        "actual_phonemes": actual,
        "PCC": scores["consonant"],
        "PVC": scores["vowel"],
        "alignment": alignment,
        "unclassified_target_phonemes": [
            p for p in target if classify(p) == "unclassified"
        ],
        "note": (
            "Scores reflect exact symbolic matches after configured "
            "normalization. They are not independently verified "
            "clinical scores."
        )
    }

    specific_path = Path(f"{OUTPUT_FILE}/{target_path.stem}.json")

    with specific_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print("\nPCC and PVC Analysis")
    print("-" * 30)
    print(f"PCC: {scores['consonant']['percentage']}%")
    print(f"PVC: {scores['vowel']['percentage']}%")
    print(f"Results saved to: {specific_path}")

    return specific_path

if __name__ == "__main__":
    pcc_pvc_main(
        Path(BASE_DIR / "target_phonemes" / "session_1" / "session_1.json"),
        Path(BASE_DIR / "phoneme_word" / "session_1.json")
    )
