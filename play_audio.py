import sounddevice as sd
import scipy.io.wavfile as wav

rate, data = wav.read("audio.wav")

sd.play(data, rate)
sd.wait()