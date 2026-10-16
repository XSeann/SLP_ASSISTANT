
# ipa_reference.py
# IPA reference for phonetic inventory analysis.

# ==================================================
# CONSONANTS
# ==================================================
CONSONANTS = {
    # Plosives
    "p", "b", "t", "d", "ʈ", "ɖ", "c", "ɟ", "k", "g", "q", "ɢ", "ʔ",

    # Nasals
    "m", "ɱ", "n", "ɳ", "ɲ", "ŋ", "ɴ",

    # Trills and taps
    "ʙ", "r", "ʀ", "ⱱ", "ɾ", "ɽ",

    # Fricatives
    "ɸ", "β", "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ",
    "ʂ", "ʐ", "ç", "ʝ", "x", "ɣ", "χ", "ʁ", "ħ", "ʕ",
    "h", "ɦ", "ɕ", "ʑ", "ɧ",

    # Lateral fricatives
    "ɬ", "ɮ",

    # Approximants
    "ʋ", "ɹ", "ɻ", "j", "ɰ", "w", "ɥ", "ɺ",

    # Lateral approximants
    "l", "ɭ", "ʎ", "ʟ",

    # Common affricates (single phoneme units)
    "t͡s", "d͡z", "t͡ʃ", "d͡ʒ", "t͡ɕ", "d͡ʑ",
    "ʈ͡ʂ", "ɖ͡ʐ", "p͡f", "b͡v",
    "ts", "dz", "tʃ", "dʒ",
}

# ==================================================
# VOWELS
# ==================================================
VOWELS = {
    # Close vowels
    "i", "y", "ɨ", "ʉ", "ɯ", "u",

    # Near-close vowels
    "ɪ", "ʏ", "ʊ",

    # Close-mid vowels
    "e", "ø", "ɘ", "ɵ", "ɤ", "o",

    # Mid vowel
    "ə",

    # Open-mid vowels
    "ɛ", "œ", "ɜ", "ɞ", "ʌ", "ɔ",

    # Near-open vowels
    "æ", "ɐ",

    # Open vowels
    "a", "ɶ", "ä", "ɑ", "ɒ",

    # Common length-marked vowels
    "iː", "uː", "ɑː", "ɔː", "ɜː", "ɚ", "ɝ",
}

# ==================================================
# DIPHTHONGS
# Common English diphthongs and additional IPA
# vowel-glide combinations.
# ==================================================
DIPHTHONGS = {
    # Common English diphthongs
    "eɪ", "aɪ", "ɔɪ", "aʊ", "oʊ",

    # Common in some English accents
    "ɪə", "eə", "ʊə", "ɛə",

    # Other possible vowel-glide sequences
    "ɑɪ", "ɑʊ", "ɔə", "ɪʊ", "ʊɪ",
    "əʊ", "ɛɪ", "æɪ", "æʊ",
}

# ==================================================
# OTHER IPA SYMBOLS / DIACRITICS
# ==================================================
OTHER_SYMBOLS = {
    "ˈ", "ˌ", ".", "ː", "ˑ", "̆", "̃", "̩", "̯",
    "ʰ", "ʷ", "ʲ", "ˠ", "ˤ", "̥", "̬", "̪",
    "̺", "̻", "̟", "̠", "̈", "̽", "̹", "̜",
    "̝", "̞", "̘", "̙", "̚", "̤", "̰",
    "ɫ", "ɾ", "ʔ", "ʕ", "ɦ",
}

# Combined reference set.
IPA_SYMBOLS = CONSONANTS | VOWELS | DIPHTHONGS | OTHER_SYMBOLS

# ==================================================
# NORMALIZATION
# Merge token sequences representing one phoneme.
# ==================================================
COMBINATIONS_TO_MERGE = {
    ("o", "ʊ"): "oʊ",
    ("ə", "ʊ"): "əʊ",
    ("e", "ɪ"): "eɪ",
    ("a", "ɪ"): "aɪ",
    ("ɔ", "ɪ"): "ɔɪ",
    ("a", "ʊ"): "aʊ",
    ("ɪ", "ə"): "ɪə",
    ("ɛ", "ə"): "ɛə",
    ("ʊ", "ə"): "ʊə",
    ("t", "ʃ"): "tʃ",
    ("d", "ʒ"): "dʒ",
    ("t", "s"): "ts",
    ("d", "z"): "dz",
}


def normalize_phonemes(phonemes):
    """Merge recognized multi-token phonemes."""
    result = []
    i = 0

    while i < len(phonemes):
        merged = False

        # Try longer combinations first if more are added later.
        for size in range(min(3, len(phonemes) - i), 1, -1):
            sequence = tuple(phonemes[i:i + size])

            if sequence in COMBINATIONS_TO_MERGE:
                result.append(COMBINATIONS_TO_MERGE[sequence])
                i += size
                merged = True
                break

        if not merged:
            result.append(phonemes[i])
            i += 1

    return result


def is_known_ipa(symbol):
    """Check whether a symbol is in this reference."""
    return symbol in IPA_SYMBOLS
