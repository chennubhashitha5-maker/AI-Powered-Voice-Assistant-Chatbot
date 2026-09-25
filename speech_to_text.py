import whisper

model = whisper.load_model("small")

def speech_to_text(audio_file):

    result = model.transcribe(
        audio_file,
        language="en",
        beam_size=5,
        best_of=5
    )

    return result["text"].strip()