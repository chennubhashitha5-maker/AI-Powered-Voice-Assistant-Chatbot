import requests

def classify_query(query):

    prompt = f"""
Classify the query into ONE category.

FACULTY:
Questions about a faculty member's profile, qualification,
designation, experience, joining date, or personal information.

TIMETABLE:
Questions about subjects, teaching schedules, classes,
rooms, sections, timetables, free faculty, vacant rooms,
current class, next class, or faculty location.

Return ONLY:

FACULTY
or
TIMETABLE

Query:
{query}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    result = response.json()["response"].strip().upper()

    if "FACULTY" in result:
        return "FACULTY"

    if "TIMETABLE" in result:
        return "TIMETABLE"

    return "UNKNOWN"