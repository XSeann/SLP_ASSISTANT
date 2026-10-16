"""
Integration adapter for your existing SLP scripts.

IMPORTANT:
- This starter deliberately does not guess command-line arguments for your scripts.
- Set TARGET_PHONEMIZER_SCRIPT and PROCESSING_SCRIPTS below after checking how each
  existing script receives the record name, target sentence, and audio path.
- If a script is importable as a function, calling that function directly is often cleaner.
"""
from datetime import datetime
from pathlib import Path
import json

from mfa_subprocess import mfa_main
from transcription import transcription_main
from phoneme_recognition import phoneme_recognition_main
from phoneme_boundary import phoneme_boundary_main
from phonetic_inventory import phonetic_inventory_main
from pcc_pvc import pcc_pvc_main
from tttr_syllable_shape import templin_ttr_syllable_main
from soda import soda_main

ROOT = Path(__file__).resolve().parents[1]
RECORDINGS = ROOT / "target_phonemes"
RESULTS = ROOT / "data" / "results"

# Update these paths to match your actual files.
TARGET_PHONEMIZER_SCRIPT = ROOT / "target_phonemizer.py"
PROCESSING_SCRIPTS = [
    ROOT / "mfa_subprocess.py",
    ROOT / "transcription.py",
    ROOT / "phoneme_recognition.py",
    ROOT / "phoneme_boundary.py",
    ROOT / "phonetic_inventory.py",
    ROOT / "pcc_pvc.py",
    ROOT / "tttr_syllable_shape.py",
    ROOT / "soda.py",
]

def process_recording(record_name, expected_words=None):
    session_folder = RECORDINGS / record_name

    audio_path = session_folder / f"{record_name}.wav"
    txt_path = session_folder / f"{record_name}.txt"
    target_json_path = session_folder / f"{record_name}.json"

    if not audio_path.exists():
        raise FileNotFoundError(f"Missing audio: {audio_path}")

    if not txt_path.exists():
        raise FileNotFoundError(f"Missing target TXT: {txt_path}")

    result_folder = RESULTS / record_name
    result_folder.mkdir(parents=True, exist_ok=True)

    steps = []

    # 1. Forced alignment using expected words
    mfa_result = mfa_main(audio_path, txt_path)
    mfa_json_path = Path(mfa_result["json"])
    steps.append({
        "name": "mfa_subprocess.py",
        "status": "success",
        "json": str(mfa_result["json"])
    })

    # 2. Audio transcription using faster-whisper
    transcription_json = transcription_main(audio_path)
    steps.append({
        "name": "transcription.py",
        "status": "success",
        "json": str(transcription_json)
    })

    # 3. Recognize actual phonemes
    phoneme_json_path = phoneme_recognition_main(audio_path)

    # 4. Assign phonemes to MFA word intervals
    phoneme_boundary_main(phoneme_json_path, mfa_json_path)

    # 5. Generate phonetic inventory
    inventory_report = phonetic_inventory_main(target_json_path, phoneme_json_path)

    # 6. Calculate PCC and PVC
    pcc_pvc_report = pcc_pvc_main(target_json_path, phoneme_json_path)

    # 7. Templin TTR and syllable-shape analysis
    tttr_report = templin_ttr_syllable_main(
        phoneme_json_path,
        transcription_json
    )

    # 8. SODA analysis
    soda_report = soda_main(
        target_json_path,
        phoneme_json_path
    )

    target_data = {}
    if target_json_path.exists():
        target_data = json.loads(
            target_json_path.read_text(encoding="utf-8")
        )

    summary = {
        "record_name": record_name,
        "audio_path": str(audio_path),
        "expected_words": target_data.get(
            "target_input", {}
        ).get("sentence", expected_words or ""),
        "steps": steps,
        "result_files": [
            str(mfa_result["json"]),
            str(transcription_json),
            str(target_json_path)
        ]
    }

    summary_path = result_folder / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    return summary