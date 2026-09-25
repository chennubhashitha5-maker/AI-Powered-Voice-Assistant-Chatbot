from timetable_retriever import retrieve_timetable

query = input("Ask Timetable Question: ")

docs = retrieve_timetable(query)

print("\nResults:\n")

for doc in docs:
    print(doc)
    print("-" * 50)