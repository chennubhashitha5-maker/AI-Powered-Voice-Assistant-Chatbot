from faculty_retriever import retrieve_faculty

query = input("Ask Faculty Question: ")

docs = retrieve_faculty(query)

print("\nResults:\n")

for doc in docs:
    print(doc)
    print("-" * 50)