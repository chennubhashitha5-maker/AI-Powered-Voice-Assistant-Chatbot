from query_classifier import classify_query

query = input("Question: ")

category = classify_query(query)

print("\nCategory:", category)