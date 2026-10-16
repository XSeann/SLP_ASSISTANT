
from pathlib import Path
import subprocess
import json

from praatio import textgrid

# ======================================================
# CONFIGURATION
# ======================================================

PROJECT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = PROJECT_DIR / "mfa_aligner"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DICTIONARY = "english_us_mfa"
ACOUSTIC_MODEL = "english_mfa"

# ======================================================
# RUN MFA
# ======================================================

def run_mfa(audio_path, txt_path, txtgrid_path):
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    if not txt_path.exists():
        raise FileNotFoundError(
            f"Transcript file not found: {txt_path}"
        )

    command = [
        "conda", "run", "--no-capture-output",
        "-n", "mfa",
        "mfa", "align_one",
        "--output_format", "long_textgrid",
        "--overwrite",
        str(audio_path),
        str(txt_path),
        DICTIONARY,
        ACOUSTIC_MODEL,
        str(txtgrid_path),
    ]

    print("Running Montreal Forced Aligner...")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(
            "MFA alignment failed.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    if not txtgrid_path.exists():
        raise FileNotFoundError(
            f"MFA did not create: {txtgrid_path}\n"
            f"{result.stdout}"
        )

    print("MFA alignment completed successfully.")

    return 

# ======================================================
# CONVERT TEXTGRID TO WORD-LEVEL JSON
# ======================================================

def textgrid_to_json(textgrid_path, json_path, file_name):
    tg = textgrid.openTextgrid(
        str(textgrid_path),
        includeEmptyIntervals=False
    )

    word_tier_name = next(
        (name for name in tg.tierNames
         if name.lower() == "words"),
        None
    )

    if word_tier_name is None:
        raise ValueError(
            f"No words tier found: {tg.tierNames}"
        )

    words = []

    for start, end, label in tg.getTier(word_tier_name).entries:
        label = label.strip()

        if not label or label.lower() in {
            "sil", "sp", "spn", "<eps>"
        }:
            continue

        words.append({
            "word": label,
            "start": round(float(start), 3),
            "end": round(float(end), 3)
        })

    result = {
        "file": file_name,
        "alignment_model": ACOUSTIC_MODEL,
        "words": words
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    return json_path

def mfa_main(audio_path, txt_path):
    audio_path = Path(audio_path)
    txt_path = Path(txt_path)

    output_folder = OUTPUT_DIR / audio_path.stem
    output_folder.mkdir(parents=True, exist_ok=True)

    grid_path = output_folder / f"{audio_path.stem}.TextGrid"
    json_path = output_folder / f"{audio_path.stem}.json"

    run_mfa(audio_path, txt_path, grid_path)
    textgrid_to_json(grid_path, json_path, audio_path.stem)

    return {
        "audio": audio_path,
        "textgrid": grid_path,
        "json": json_path
    }

# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":
    mfa_main(Path(f"{PROJECT_DIR}/target_phonemes/session_4/session_4.wav"),
             Path(f"{PROJECT_DIR}/target_phonemes/session_4/session_4.txt"))