from faster_whisper import WhisperModel
from pathlib import Path
import os
import json

# ======================================================
# CONFIGURATION
# ======================================================

# FILE_NAME = "session_2"

# INPUT_AUDIO = fr"C:\Users\lenovo\Documents\CODER\PYTHON\SLP_AI_Assistant_2\audio\audio_records\original_record\\{FILE_NAME}.wav"

PROJECT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = PROJECT_DIR / "transcription"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = str(PROJECT_DIR / "model" / "whisper-medium")

DEVICE = "cpu"

COMPUTE_TYPE = "int8"

def transcription_main(path):

    print("Loading Whisper model...")

    model = WhisperModel(
        MODEL_PATH,
        device=DEVICE,
        compute_type=COMPUTE_TYPE
    )

    print("Transcribing audio...")

    segments, info = model.transcribe(
        path,
        word_timestamps=True,
        beam_size=5,
        language="en"
    )

    print(f"Detected Language : {info.language}")
    print(f"Language Probability : {info.language_probability:.2f}")

    # ======================================================
    # SAVE RESULTS
    # ======================================================

    segments_list = []

    words = ""
    
    for segment in segments: 
        # Make sure word timestamps actually exist 
        if segment.words is None: 
            continue 
        for word in segment.words: 
            segments_list.append({
                "model": "whisper-medium", 
                "start": round(word.start, 3), 
                "end": round(word.end, 3), 
                "word": word.word.strip() 
            })
            
            words += word.word.strip() + " "

    # ====================================================== 
    # SAVE JSON 
    # ======================================================

    results = {  
        "audio_file": f"{path.stem}.wav",
        "model": "whisper-medium",
        "transcript": words.strip(),
        "segments": segments_list
    }

    filepath = Path(f"{OUTPUT_DIR}/{Path(path).stem}.json")

    with open(filepath, "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, indent=4, ensure_ascii=False)

    print("\n===================================")
    print("TRANSCRIPTION COMPLETED")
    print("===================================")
    print(fr"JSON       : {OUTPUT_DIR}/{path.stem}.json")

    return filepath

    '''
    [0.00 - 4.00] Hello, hello, hello, hello testing testing 
    [4.01 - 8:00] Ako nga pala si Seann Ej Malimpenet 
    [8:01 - 12:00] Ang gagawin ko ngayon is itetest ko kung 
    [12:01 - 16:00] Kaya bang magbasa ng english can 
    [16:01 - 19:00] You read english and diko alam ang gagawin ko

    transcript = [] #[]
    
        for segment in segments:
    
            #transcript += segment.text.strip() + " "
    
            transcript.append({
                #"audio_file": f"{FILE_NAME}.wav",
                "model": "whisper-medium",
                "start": segment.start,
                "end": segment.end,
                "word": segment.text.strip()    
            })
    '''

if __name__ == "__main__":
    # Example usage
    input_audio_path = Path(r"C:\Users\lenovo\Documents\CODER\PYTHON\SLP_AI_Assistant_2\target_phonemes\session_1\session_1.wav")
    transcription_main(input_audio_path)