from record_audio import record_audio
from speech_to_text import speech_to_text

from router import route_query
from answer_generate import generate_answer

from text_to_speech import speak


def prepare_for_speech(text):

    replacements = {
        "Ph.D": "Doctor of Philosophy",
        "B.Tech": "Bachelor of Technology",
        "M.Tech": "Master of Technology",
        "M.E": "Master of Engineering",
        "MCA": "Master of Computer Applications",
        "M.Sc": "Master of Science",
        "EEE": "Electrical and Electronics Engineering",
        "CSE": "Computer Science and Engineering",
        "IoT": "Internet of Things",
        "EV": "Electrical Vehicles",
        "PIDC": "P I D C",
        "QIPPG": "Q I P P G"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


print("\nVOICE ASSISTANT STARTED")

while True:

    audio_file = record_audio()

    query = speech_to_text(audio_file)

    print("\nYou Said:", query)

    if not query:
        continue

    result = route_query(query)

    result_type = result.get("type")
    data = result.get("data")

    # ---------------------------------
    # TIMETABLES -> SCREEN ONLY
    # ---------------------------------
    if result_type in ["SECTION_TIMETABLE", "DAY_TIMETABLE"]:

        print("\nTimetable displayed on screen.\n")

        if result_type == "SECTION_TIMETABLE":

            current_day = ""

            for row in data:

                day, period, subject, faculty, start, end, room = row

                if day != current_day:
                    current_day = day
                    print(f"\n===== {day} =====")

                print(
                    f"P{period} | {subject} | {faculty} | {room} | {start}-{end}"
                )

        elif result_type == "DAY_TIMETABLE":

            print("\n===== DAY TIMETABLE =====\n")

            for row in data:

                period, subject, faculty, room, start, end = row

                print(
                    f"P{period} | {subject} | {faculty} | {room} | {start}-{end}"
                )

        continue

    # ---------------------------------
    # ALL OTHER QUERIES
    # ---------------------------------
    answer = generate_answer(
        query,
        result_type,
        data
    )

    print("\nAssistant:", answer)

    speak_text = prepare_for_speech(answer)

    speak(speak_text)