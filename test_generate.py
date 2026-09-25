from router import route_query
from answer_generator import generate_answer


# -----------------------------
# SECTION TIMETABLE
# -----------------------------
def print_section_timetable(data):

    print("\nSECTION TIMETABLE\n")

    current_day = ""

    for row in data:

        day, period, subject, faculty, start, end, room = row

        if day != current_day:
            current_day = day
            print(f"\n===== {day} =====")

        print(
            f"P{period} | {subject} | {faculty} | {room} | {start}-{end}"
        )


# -----------------------------
# DAY TIMETABLE
# -----------------------------
def print_day_timetable(data):

    print("\nDAY TIMETABLE\n")

    for row in data:

        period, subject, faculty, room, start, end = row

        print(
            f"P{period} | {subject} | {faculty} | {room} | {start}-{end}"
        )


# -----------------------------
# ROOM TIMETABLE
# -----------------------------
def print_room_timetable(data):

    print("\nROOM TIMETABLE\n")

    for row in data:

        day, period, subject, faculty, section, start, end = row

        print(
            f"{day} | P{period} | {subject} | {faculty} | {section} | {start}-{end}"
        )


# -----------------------------
# MAIN
# -----------------------------
query = input("Question: ")

result = route_query(query)

print("\nRetrieved Result:\n")
print(result)

result_type = result.get("type")

# -----------------------------
# TIMETABLES -> PYTHON OUTPUT
# -----------------------------
if result_type == "SECTION_TIMETABLE":

    print_section_timetable(result["data"])

elif result_type == "DAY_TIMETABLE":

    print_day_timetable(result["data"])

elif result_type == "ROOM_TIMETABLE":

    print_room_timetable(result["data"])

# -----------------------------
# EVERYTHING ELSE -> MISTRAL
# -----------------------------
else:

    print("\nGenerating Answer...\n")

    answer = generate_answer(
        query,
        result
    )

    print(answer) 