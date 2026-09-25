import sounddevice as sd
import scipy.io.wavfile as wav
import keyboard

SAMPLE_RATE = 16000

def record_audio():

    print("\n🎤 Press S to START recording")

    keyboard.wait("s")

    print("🔴 Recording... Press E to STOP")

    recording = []

    def callback(indata, frames, time, status):
        recording.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=callback
    )

    stream.start()

    keyboard.wait("e")

    stream.stop()
    stream.close()

    import numpy as np

    audio = np.concatenate(recording, axis=0)

    wav.write(
        "audio.wav",
        SAMPLE_RATE,
        audio
    )

    print("✅ Audio Saved")

    return "audio.wav"