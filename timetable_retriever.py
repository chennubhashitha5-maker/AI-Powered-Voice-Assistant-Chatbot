import chromadb
import requests

client = chromadb.PersistentClient(path="./chroma_db")

timetable_collection = client.get_collection(
    "timetable_collection"
)

def retrieve_timetable(query):

    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": query
        }
    )

    query_embedding = response.json()["embedding"]

    results = timetable_collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    return results["documents"][0]