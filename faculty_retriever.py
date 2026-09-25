import chromadb
import requests

# Connect to ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")

faculty_collection = client.get_collection(
    "faculty_collection"
)


def retrieve_faculty(query):

    # Generate query embedding using Ollama
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": query
        }
    )

    query_embedding = response.json()["embedding"]

    # Search Chroma using embedding
    results = faculty_collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        include=["documents", "distances"]
    )

    # Get similarity distance
    distance = results["distances"][0][0]

    return results["documents"][0][0]