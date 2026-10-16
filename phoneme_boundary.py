
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def phoneme_boundary_main(phoneme_json, mfa_json):
    phoneme_json = Path(phoneme_json)
    mfa_json = Path(mfa_json)

    if not phoneme_json.is_file():
        raise FileNotFoundError(f"Phoneme JSON not found: {phoneme_json}")
    if not mfa_json.is_file():
        raise FileNotFoundError(f"MFA JSON not found: {mfa_json}")

    with phoneme_json.open("r", encoding="utf-8") as f:
        actual_data = json.load(f)

    with mfa_json.open("r", encoding="utf-8") as f:
        mfa_data = json.load(f)

    phonemes = actual_data.get("phonemes", [])
    words = mfa_data.get("words", [])

    if not words:
        raise ValueError(f"No word intervals found in {mfa_json}")
    if not phonemes:
        actual_data["phoneme_words"] = ""
        with phoneme_json.open("w", encoding="utf-8") as f:
            json.dump(actual_data, f, indent=4, ensure_ascii=False)
        return phoneme_json

    # Assign each phoneme to the word with the greatest
    # positive overlap between their time intervals.
    word_phonemes = [[] for _ in words]

    for phone in phonemes:
        phone_start = float(phone["start"])
        phone_end = float(phone["end"])
        best_word = None
        best_overlap = 0.0

        if phone_end <= phone_start:
            continue

        for index, word in enumerate(words):
            word_start = float(word["start"])
            word_end = float(word["end"])

            overlap = max(
                0.0,
                min(phone_end, word_end) -
                max(phone_start, word_start)
            )

            if overlap > best_overlap:
                best_overlap = overlap
                best_word = index

        # Ignore phonemes that do not overlap any word interval.
        if best_word is not None:
            symbol = phone.get("phoneme", "")
            if symbol:
                word_phonemes[best_word].append(symbol)

    # Preserve the existing output format:
    # one phoneme string per word, separated by spaces.
    phoneme_boundary = " ".join(
        "".join(symbols) for symbols in word_phonemes
    )

    actual_data["phoneme_words"] = phoneme_boundary

    with phoneme_json.open("w", encoding="utf-8") as f:
        json.dump(actual_data, f, indent=4, ensure_ascii=False)

    print(f"Phoneme words: {phoneme_boundary}")
    print(f"Updated JSON: {phoneme_json}")

    return phoneme_json


if __name__ == "__main__":
    phoneme_boundary_main(
        PROJECT_ROOT / "phoneme_word" / "session_4.json",
        PROJECT_ROOT / "mfa_aligner" / "session_4" / "session_4.json"
    )
