
import json
import re
from pathlib import Path
from datetime import datetime
from phonemizer import phonemize
from ipa_char import (CONSONANTS, VOWELS, DIPHTHONGS, IPA_SYMBOLS)

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "target_phonemes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_input(prompt):
    while True:
        value = re.sub(r"\s+", " ", input(prompt).strip())
        if value:
            return value
        print("ERROR: Input cannot be empty.")


def tokenize_words(sentence):
    return re.findall(
        r"[^\W\d_]+(?:['’-][^\W\d_]+)*",
        sentence,
        flags=re.UNICODE
    )

def normalize_word(word):
    return word.replace("’", "'").replace("‘", "'").lower().strip()

def parse_phonemes(text):
    # Keep IPA modifiers attached to their preceding phoneme.
    # modifiers = set("ːˑʰʱʲʷʸ̥̯̃̈̆̄́̀˞")
    phonemes = []
    combine_state = False
    
    txt_len = len(re.sub(r"\s+", "", text))
    
    for ind in range(txt_len): 
        combine = text[ind] + text[ind+1] if ind+1 != txt_len else ""

        if combine_state:
            combine_state = False
            continue

        if text[ind] in "|/":
            continue

        if combine in IPA_SYMBOLS:
            combine_state = True
            phonemes.append(text[ind] + text[ind+1])  

        if combine_state == False:
            phonemes.append(text[ind])

    return phonemes


def phonemize_word(word):
    try:
        result = phonemize(
            normalize_word(word),
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            njobs=1
        )

        return parse_phonemes(result) if result else []
    except Exception as error:
        print(f"WARNING: Could not phonemize '{word}': {error}")
        return []


def safe_filename(title):
    name = re.sub(r"[^a-zA-Z0-9]+", "_", title.lower()).strip("_")
    return (name or "target_sentence")[:80]


def target_phonemizer_main(title, sentence):
    print("\n=== TARGET WORD PHONEMIZATION ===")
    title = re.sub(r"\s+", " ", title.strip())
    sentence = re.sub(r"\s+", " ", sentence.strip())

    if not title or not sentence:
        raise ValueError("Session title and sentence are required.")

    words = tokenize_words(sentence)

    if not words:
        print("ERROR: No valid words detected.")
        return

    word_results = []
    for index, word in enumerate(words, start=1):
        phonemes = phonemize_word(word)
        print("PHONEMES: ", phonemes)
        word_results.append({
            "index": index,
            "word": word,
            "normalized_word": normalize_word(word),
            "phonemes": phonemes
        })
        print(f"{index}. {word} -> {' '.join(phonemes) or '[NONE]'}")

    combined = [
        phoneme
        for item in word_results
        for phoneme in item["phonemes"]
    ]

    target_data = {
        "module": "Target Word Phonemization",
        "target_input": {
            "title": title,
            "sentence": sentence,
            "word_count": len(words),
            "created_at": datetime.now().isoformat(timespec="seconds")
        },
        "words": word_results,
        "phoneme_recognition": {
            "phoneme_sequence": " ".join(combined),
            "phonemes": combined,
            "phoneme_count": len(combined)
        }
    }

    base = safe_filename(title)

    specific_path = OUTPUT_DIR / base
    specific_path.mkdir(parents=True, exist_ok=True)

    json_path = specific_path / f"{base}.json"
    txt_path = specific_path / f"{base}.txt"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(target_data, file, ensure_ascii=False, indent=4)

    # TXT contains only the target words, one word per line.
    txt_path.write_text(" ".join(words) + "\n", encoding="utf-8")

    print(f"\nCombined target phonemes: {' '.join(combined)}")
    print(f"JSON saved: {json_path}")
    print(f"TXT saved:  {txt_path}")

    return {
        "folder": specific_path,
        "base": base,
        "json_path": json_path,
        "txt_path": txt_path,
        "data": target_data
    }

if __name__ == "__main__":
    target_phonemizer_main("session #30", "Hello look what i brought to the park")
