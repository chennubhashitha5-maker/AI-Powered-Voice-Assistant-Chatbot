import chromadb

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_collection("faculty_collection")

data = collection.get()

print("Total Documents:", len(data["documents"]))

print("\nFirst 5 Documents:\n")

for i in range(min(5, len(data["documents"]))):
    print("--------------------------------")
    print(data["documents"][i])