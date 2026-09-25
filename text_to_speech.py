import pyttsx3

def speak(text):

    engine = pyttsx3.init()

    engine.setProperty("rate", 170)

    engine.say(str(text))

    engine.runAndWait()

    engine.stop()