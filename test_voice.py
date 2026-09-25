from record_audio import record_audio
from speech_to_text import speech_to_text

audio_file = record_audio()

text = speech_to_text(audio_file)

print("\nYou Said:", text)