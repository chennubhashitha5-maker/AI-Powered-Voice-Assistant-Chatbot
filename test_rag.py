from query_classifier import classify_query
from faculty_retriever import retrieve_faculty
from timetable_retriever import retrieve_timetable
from answer_generator import generate_answer

query = input("Question: ")

category = classify_query(query)

print("Category:", category)

if category == "FACULTY":
    docs = retrieve_faculty(query)
else:
    docs = retrieve_timetable(query)

context = "\n\n".join(docs)

answer = generate_answer(query, context)

print("\nAnswer:\n")
print(answer)