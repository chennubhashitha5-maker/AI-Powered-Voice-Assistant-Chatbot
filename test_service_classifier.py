from service_classifier import classify_service_query

query = input("Question: ")

result = classify_service_query(query)

print("\nCategory:", result)