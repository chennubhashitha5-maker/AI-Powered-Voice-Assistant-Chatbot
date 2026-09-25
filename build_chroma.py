import psycopg2
import requests
import chromadb

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

# -----------------------------
# ChromaDB
# -----------------------------
client = chromadb.PersistentClient(path="./chroma_db")

# Delete old collections if they exist
try:
    client.delete_collection("faculty_collection")
except:
    pass

try:
    client.delete_collection("timetable_collection")
except:
    pass

faculty_collection = client.create_collection(
    name="faculty_collection"
)

timetable_collection = client.create_collection(
    name="timetable_collection"
)

# -----------------------------
# Faculty Data
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

faculty_rows = cur.fetchall()

for i, row in enumerate(faculty_rows):

    document = f"""
Faculty Profile

Faculty Name: {row[0]}

Designation: {row[1]}

Qualification: {row[2]}

Date of Joining: {row[3]}

Experience: {row[4]} months
"""

    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": document
        }
    )

    embedding = response.json()["embedding"]

    faculty_collection.add(
        ids=[f"faculty_{i}"],
        documents=[document],
        embeddings=[embedding],
        metadatas=[{
            "faculty_name": row[0]
        }]
    )

    print(f"Faculty Added: {row[0]}")

# -----------------------------
# Timetable Data
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

timetable_rows = cur.fetchall()

for i, row in enumerate(timetable_rows):

    document = f"""
Faculty: {row[0]}
Subject: {row[1]}
Day: {row[2]}
Period: {row[3]}
Time: {row[4]} to {row[5]}
Section: {row[6]}
Room: {row[7]}
"""

    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": document
        }
    )

    embedding = response.json()["embedding"]

    timetable_collection.add(
        ids=[f"timetable_{i}"],
        documents=[document],
        embeddings=[embedding],
        metadatas=[{
            "faculty": row[0],
            "subject": row[1]
        }]
    )

    print(f"Timetable Added: {i+1}")

cur.close()
conn.close()

print("\nChromaDB Build Complete")