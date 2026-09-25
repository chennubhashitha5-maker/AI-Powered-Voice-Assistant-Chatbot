from rapidfuzz import process, fuzz

FACULTY_NAMES = [

    "A.Aruna",
    "A.Sri Chaitanya",
    "A.Sudhakar",
    "Ch.Divya",
    "Ch.Suresh Babu",
    "D.Ritwik",
    "E.Narmadha",
    "Jagadesh",
    "K.Prasanth",
    "M.Anitha",
    "M.Aruna Safali",
    "M.Himaja Joythi",
    "M.Roja",
    "Md.Eliaz",
    "P.Mareswaramma",
    "P.Narasimham",
    "P.Pavani",
    "Parvathi",
    "R.Kiran Kumar",
    "R.Madhukanth",
    "Ranjith",
    "Sree Kumar",
    "T.Swathi",
    "V.Rama Krishna",

    "D.Navatha",
    "K.Sireesha"
]

def match_faculty_name(query):

    result = process.extractOne(
        query,
        FACULTY_NAMES,
        scorer=fuzz.WRatio
    )

    if result is None:
        return None

    faculty_name = result[0]
    score = result[1]

    print("Score:", score)

    if score >= 40:
        return faculty_name

    return None