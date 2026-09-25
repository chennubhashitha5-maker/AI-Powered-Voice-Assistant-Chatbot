import requests


def classify_service_query(query):

    prompt = f"""
Classify the timetable query into ONE category.

Categories:

LOOKUP
SECTION_TIMETABLE
CURRENT_CLASS
VACANT_ROOMS
NEXT_CLASS
ROOM_STATUS
DAY_TIMETABLE 
FIRST_CLASS
LAST_CLASS
CLASS_BY_TIME



Rules:
- Return ONLY one category name
- No explanation
- No extra text

Examples:

Who teaches ML?
LOOKUP

what subjects Eliaz teach?
LOOKUP 

Which faculty handles Probability and Statistics?
LOOKUP

Show timetable for third CSM-A?
SECTION_TIMETABLE

What class is going on in t9 now?
CURRENT_CLASS

Which rooms are vacant now?
VACANT_ROOMS

What is the next class for third csm b?
NEXT_CLASS

Is T9 free now?
ROOM_STATUS

What is happening in T9 now?
ROOM_STATUS

Who is in T13 now?
ROOM_STATUS

Show Monday timetable for CSM-2
DAY_TIMETABLE

What is the timetable for CSM-3B on Friday?
DAY_TIMETABLE

What is the first class on Monday for CSM-2?
FIRST_CLASS

what is the first class for second csm on tuesday?
FIRST_CLASS

What is the last class on Friday for CSM-3A?
LAST_CLASS

what is the last class for second csm on tuesday?
LAST_CLASS

What class is at 11:30 for CSM-3A on Monday?
CLASS_BY_TIME

What is the class from 12.20 to 1.10 for second csm on tuesday?
CLASS_BY_TIME

Return ONLY category.

Query:
{query}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )

        result = response.json()["response"].strip().upper()

        categories = [
            "LOOKUP",
            "SECTION_TIMETABLE",
            "CURRENT_CLASS",
            "VACANT_ROOMS",
            "NEXT_CLASS",
            "ROOM_STATUS",
            "DAY_TIMETABLE",
            "FIRST_CLASS",
            "LAST_CLASS",
            "CLASS_BY_TIME"

            
        ]

        for c in categories:
            if c in result:
                return c

        return "UNKNOWN"

    except Exception as e:
        print("Service classifier error:", e)
        return "UNKNOWN"-answer_generate.py