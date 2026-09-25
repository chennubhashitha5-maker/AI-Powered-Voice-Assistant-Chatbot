import pandas as pd
import chromadb
import ollama


# -------------------------
# Load CSV files
# -------------------------

faculty = pd.read_csv("faculty.csv")
timetable = pd.read_csv("time_table.csv")


# -------------------------
# Clean data
# -------------------------

# Remove empty columns
faculty = faculty.loc[:, ~faculty.columns.str.contains("^Unnamed")]

# Remove spaces from column names
faculty.columns = faculty.columns.str.strip()
timetable.columns = timetable.columns.str.strip()


# Remove empty rows
faculty = faculty.dropna(subset=["faculty_name"])
timetable = timetable.dropna(subset=["faculty", "subject"])


# -------------------------
# Create documents list
# -------------------------

documents = []


# Faculty documents
for index, row in faculty.iterrows():

    text = f"""
    Faculty Name: {row['faculty_name']}.
    Faculty ID: {row['faculty_id']}.
    Designation: {row['faculty_designation']}.
    Qualification: {row['faculty_qualification']}.
    Date of Joining: {row['date_of_joining']}.
    Experience: {row['experience_in_months']} months.
    """

    documents.append(text)


# Timetable documents
for index, row in timetable.iterrows():

    text = f"""
    Room {row['room_number']} has {row['subject']}
    class on {row['day']} during period {row['period']}.
    The class is handled by faculty {row['faculty']}
    for section {row['section']}.
    Timing is from {row['starting_time']}
    to {row['ending_time']}.
    """

    documents.append(text)


# -------------------------
# Check generated documents
# -------------------------

print("TOTAL DOCUMENTS CREATED:", len(documents))

print("\nFIRST 3 DOCUMENTS:\n")

for doc in documents[:3]:
    print(doc)
    print("-" * 50)




# -------------------------
# Create ChromaDB Database
# -------------------------

client = chromadb.PersistentClient(path="chroma_db")

# Delete old collection if it exists
try:
    client.delete_collection("department_data")
except:
    pass

# Create fresh collection
collection = client.create_collection(
    name="department_data"
)

# -------------------------
# Generate embeddings and store data
# -------------------------

for index, doc in enumerate(documents):

    embedding = ollama.embeddings(
        model="nomic-embed-text",
        prompt=doc
    )["embedding"]

    collection.add(
        ids=[str(index)],
        documents=[doc],
        embeddings=[embedding]
    )


print("\nChromaDB created successfully!")
print("Total records stored:", collection.count())