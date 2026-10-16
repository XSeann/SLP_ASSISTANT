import os
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly
from math import gcd
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "phoneme_word"
MODEL_DIR = PROJECT_ROOT / "model" / "wav2vec2-lv-60-espeak-cv-ft"

SAMPLE_RATE = 16000
DEVICE = torch.device("cpu")

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def save_run(token_id, start_frame, end_frame, tokenizer,
             blank_id, frame_duration, duration):
    if token_id == blank_id:
        return None

    token = tokenizer.convert_ids_to_tokens(token_id)
    if not token or token.startswith("<"):
        return None

    start = min(start_frame * frame_duration, duration)
    end = min(end_frame * frame_duration, duration)

    if end <= start:
        return None

    return {
        "phoneme": token,
        "start": round(start, 3),
        "end": round(end, 3)
    }


def phoneme_recognition_main(path):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if not MODEL_DIR.is_dir():
        raise FileNotFoundError(f"Local model not found: {MODEL_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    processor = Wav2Vec2Processor.from_pretrained(
        str(MODEL_DIR), local_files_only=True
    )
    model = Wav2Vec2ForCTC.from_pretrained(
        str(MODEL_DIR), local_files_only=True
    ).to(DEVICE)
    model.eval()

    audio, original_rate = sf.read(path, dtype="float32")

    # Convert stereo/multichannel audio to mono.
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if audio.size == 0:
        raise ValueError("Audio file is empty.")
    if original_rate <= 0:
        raise ValueError(f"Invalid sample rate: {original_rate}")

    # Resample actual audio when its sample rate is not 16 kHz.
    if original_rate != SAMPLE_RATE:
        divisor = gcd(int(original_rate), SAMPLE_RATE)
        audio = resample_poly(
            audio,
            SAMPLE_RATE // divisor,
            int(original_rate) // divisor
        ).astype(np.float32)

    duration = len(audio) / SAMPLE_RATE

    inputs = processor(
        audio,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
        padding=True
    )

    with torch.inference_mode():
        logits = model(inputs.input_values.to(DEVICE)).logits[0]

    frame_ids = logits.argmax(dim=-1).cpu().tolist()
    if not frame_ids:
        raise ValueError("The model returned no output frames.")

    frame_duration = duration / len(frame_ids)
    tokenizer = processor.tokenizer
    blank_id = model.config.pad_token_id
    if blank_id is None:
        blank_id = tokenizer.pad_token_id

    phonemes = []
    previous_id = frame_ids[0]
    run_start = 0

    # Collapse consecutive identical CTC tokens.
    for i in range(1, len(frame_ids)):
        if frame_ids[i] != previous_id:
            phone = save_run(
                previous_id, run_start, i, tokenizer,
                blank_id, frame_duration, duration
            )
            if phone:
                phonemes.append(phone)

            previous_id = frame_ids[i]
            run_start = i

    # IMPORTANT: append the final run too.
    phone = save_run(
        previous_id, run_start, len(frame_ids), tokenizer,
        blank_id, frame_duration, duration
    )
    if phone:
        phonemes.append(phone)

    result = {
        "audio_file": str(path.resolve()),
        "duration": round(duration, 3),
        "sample_rate": SAMPLE_RATE,
        "phoneme_sequence": " ".join(
            item["phoneme"] for item in phonemes
        ),
        "phonemes": phonemes,
        "timing_note": (
            "Approximate CTC frame timings, not exact phoneme "
            "boundaries. Audio was resampled to 16 kHz if necessary."
        )
    }

    json_path = OUTPUT_DIR / f"{path.stem}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"Saved phoneme results: {json_path}")
    return json_path


if __name__ == "__main__":
    test_audio = PROJECT_ROOT / "target_phonemes" / "session_4" / "session_4.wav"
    phoneme_recognition_main(test_audio)
