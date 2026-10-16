
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

from ipa_char import (
    CONSONANTS,
    VOWELS,
    DIPHTHONGS,
    normalize_phonemes,
    is_known_ipa,
)

# ==================================================
# CONFIGURATION
# ==================================================
BASE_DIR = Path(__file__).resolve().parent

OUTPUT_FILE = BASE_DIR / "phonetic_inventory"
OUTPUT_FILE.mkdir(parents=True, exist_ok=True)

def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def classify_phoneme(phoneme):
    if phoneme in DIPHTHONGS:
        return "diphthong"
    if phoneme in CONSONANTS:
        return "consonant"
    if phoneme in VOWELS:
        return "vowel"
    return "other_or_unclassified"


def phonetic_inventory_main(target_file, actual_file):
    target_data = load_json(target_file)
    actual_data = load_json(actual_file)

    # Target phonemes
    target_counts = Counter()
    target_words = []

    for word_data in target_data.get("words", []):
        phonemes = normalize_phonemes(
            word_data.get("phonemes", [])
        )
        target_counts.update(phonemes)

        target_words.append({
            "index": word_data.get("index"),
            "word": word_data.get("word", ""),
            "phonemes": phonemes,
        })

    # Actual phonemes from the recording
    actual_records = actual_data.get("phonemes", [])
    actual_tokens = [
        item["phoneme"]
        for item in actual_records
        if item.get("phoneme")
    ]
    actual_tokens = normalize_phonemes(actual_tokens)
    actual_counts = Counter(actual_tokens)

    target_set = set(target_counts)
    actual_set = set(actual_counts)

    shared = sorted(target_set & actual_set)
    missing = sorted(target_set - actual_set)
    additional = sorted(actual_set - target_set)

    # Build combined inventory
    inventory = []

    for phoneme in sorted(target_set | actual_set):
        target_count = target_counts[phoneme]
        actual_count = actual_counts[phoneme]

        if target_count and actual_count:
            status = "observed_in_both"
        elif target_count:
            status = "target_not_observed"
        else:
            status = "observed_not_in_target"

        inventory.append({
            "phoneme": phoneme,
            "sound_type": classify_phoneme(phoneme),
            "known_ipa_symbol": is_known_ipa(phoneme),
            "target_count": target_count,
            "actual_count": actual_count,
            "status": status,
        })

    # Group actual inventory by sound type
    actual_inventory = {
        "consonants": sorted(
            p for p in actual_set if classify_phoneme(p) == "consonant"
        ),
        "vowels": sorted(
            p for p in actual_set if classify_phoneme(p) == "vowel"
        ),
        "diphthongs": sorted(
            p for p in actual_set if classify_phoneme(p) == "diphthong"
        ),
        "other_or_unclassified": sorted(
            p for p in actual_set
            if classify_phoneme(p) == "other_or_unclassified"
        ),
    }

    report = {
        "module": "Phonetic Inventory",
        "session": target_data.get(
            "target_input", {}
        ).get("title", "Unknown session"),
        "sentence": target_data.get(
            "target_input", {}
        ).get("sentence", ""),
        "audio_file": actual_data.get("audio_file", ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "target_phoneme_tokens": sum(target_counts.values()),
            "actual_phoneme_tokens": sum(actual_counts.values()),
            "target_unique_phonemes": len(target_set),
            "actual_unique_phonemes": len(actual_set),
            "shared_phonemes": shared,
            "target_not_observed": missing,
            "observed_not_in_target": additional,
        },
        "target_words": target_words,
        "actual_inventory_by_type": actual_inventory,
        "inventory": inventory,
        "note": (
            "This report compares transcribed phoneme symbols. "
            "It does not independently verify pronunciation or "
            "establish a clinical diagnosis. Recognition and timing "
            "may be inaccurate."
        ),
    }

    specific_path = OUTPUT_FILE / f"{target_file.stem}.json"

    with specific_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print("Phonetic inventory generated successfully!")
    print(f"Output: {specific_path}")
    print(f"Target unique phonemes: {len(target_set)}")
    print(f"Actual unique phonemes: {len(actual_set)}")
    print(f"Shared phonemes: {len(shared)}")
    print(f"Target not observed: {missing}")
    print(f"Observed not in target: {additional}")

    return specific_path

if __name__ == "__main__":
    phonetic_inventory_main(Path(BASE_DIR / "target_phonemes" / "session_1" / "session_1.json"),
                           Path(BASE_DIR / "phoneme_word" / "session_1.json"))
