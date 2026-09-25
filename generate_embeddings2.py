import psycopg2
import requests
import json

# -----------------------------
# PostgreSQL Connection
# -----------------------------
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="postgres",
    user="postgres",
    password="abc@mn"
)

cur = conn.cursor()

documents = []

# -----------------------------
# Faculty Documents
# -----------------------------
cur.execute("""
SELECT
    faculty_name,
    faculty_designation,
    faculty_qualification,
    date_of_joining,
    experience_in_months
FROM faculty
""")

for row in cur.fetchall():
    doc = f"""
Faculty Profile

{row[0]} is a faculty member in the CSM department.

Faculty Name: {row[0]}
Designation: {row[1]}
Qualification: {row[2]}
Date of Joining: {row[3]}
Experience: {row[4]} months
"""
    documents.append(doc.strip())

# -----------------------------
# Timetable Documents
# -----------------------------
cur.execute("""
SELECT
    faculty,
    subject,
    day,
    period,
    starting_time,
    ending_time,
    section,
    room_number
FROM time_table
""")

for row in cur.fetchall():
    doc = f"""
Faculty: {row[0]}
Subject: {row[1]}
Day: {row[2]}
Period: {row[3]}
Time: {row[4]} to {row[5]}
Section: {row[6]}
Room: {row[7]}
"""
    documents.append(doc.strip())

cur.close()
conn.close()

print(f"\nTotal Documents: {len(documents)}")

# -----------------------------
# Generate Embeddings
# -----------------------------
embedded_docs = []

for i, doc in enumerate(documents, start=1):

    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": doc
        }
    )

    embedding = response.json()["embedding"]

    embedded_docs.append({
        "text": doc,
        "embedding": embedding
    })

    print(f"Embedded {i}/{len(documents)}")

# -----------------------------
# Save Results
# -----------------------------
with open("embeddings.json", "w", encoding="utf-8") as f:
    json.dump(embedded_docs, f)

print("\nEmbeddings saved to embeddings.json")
print(f"Total Embeddings Generated: {len(embedded_docs)}")