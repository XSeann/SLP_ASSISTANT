from pathlib import Path
import sounddevice as sd
import soundfile as sf
import numpy as np

class AudioRecorder:
    """Simple mono WAV recorder. Requires a working microphone/input device."""
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.stream = None
        self.chunks = []
        self.paused = False
        self.path = None

    def start(self, path):
        self.path = Path(path)
        self.chunks = []
        self.paused = False
        def callback(indata, frames, time_info, status):
            if not self.paused:
                self.chunks.append(indata.copy())
        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels,
                                     dtype="float32", callback=callback)
        self.stream.start()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if not self.chunks:
            raise RuntimeError("No audio was captured. Check your microphone and try again.")
        audio = np.concatenate(self.chunks, axis=0)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(self.path), audio, self.sample_rate)
