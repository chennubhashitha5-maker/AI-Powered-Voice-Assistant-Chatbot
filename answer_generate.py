import requests


def generate_answer(query, result_type, data):

    instruction = ""

    if result_type == "FACULTY":
        instruction = "Present the faculty details clearly and naturally."

    elif result_type == "LOOKUP":
        instruction = "Answer the question directly using only the retrieved data."

    elif result_type == "VACANT_ROOMS":
        instruction = "List all vacant rooms."

    elif result_type == "CURRENT_CLASS":
        instruction = "List all current classes."

    elif result_type == "NEXT_CLASS":
        instruction = "Mention subject, faculty, room and timing."

    elif result_type == "FIRST_CLASS":
        instruction = "Mention subject, faculty, room and timing."

    elif result_type == "LAST_CLASS":
        instruction = "Mention subject, faculty, room and timing."

    elif result_type == "CLASS_BY_TIME":
        instruction = "Mention subject, faculty, room and timing."

    elif result_type == "ROOM_STATUS":
        instruction = "Describe what is happening in the room now."

    elif result_type == "ERROR":
        instruction = "Briefly describe the error."

    else:
        instruction = "I could not understand the query."

    prompt = f"""
You are a college faculty and timetable assistant.

User Question:
{query}

Retrieved Data:
{data}

Rules:
- Answer ONLY using the Retrieved Data.
- Do NOT use outside knowledge.
- Do NOT infer or assume anything.
- Keep the answer short and direct.
- Never assume a faculty member's gender.
- Never use pronouns like he, she, his or her.
- Always refer to the faculty member by the faculty name.
- If information is not present, reply:
  I could not find the requested information.
- If multiple records are present, list every record clearly.

Task:
{instruction}

Answer:
"""

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 256
                }
            },
            timeout=60
        )

        return response.json()["response"].strip()

    except Exception as e:
        print("Answer Generation Error:", e)
        return "I could not generate an answer."