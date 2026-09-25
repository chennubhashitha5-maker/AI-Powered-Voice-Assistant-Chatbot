"""
Voice-Enabled Department Assistant
-----------------------------------
Answers questions about faculty, timetables, room availability, and
free/busy status by reading two CSV files (faculty.csv, time_table.csv),
falling back to a local LLM (Ollama + ChromaDB) for open-ended questions.

This version uses native Windows SAPI (win32com) for reliable text-to-speech,
bypassing pyttsx3 initialization issues.
"""

import difflib
import logging
import re
from datetime import datetime, timedelta

import pandas as pd

# =====================================================================
# CONFIGURATION
# =====================================================================

FACULTY_CSV_PATH = "faculty.csv"
TIMETABLE_CSV_PATH = "time_table.csv"

COLLEGE_START_TIME = "09:00"
COLLEGE_END_TIME = "16:30"
WORKING_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
DAY_ORDER = {
    "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6,
}

# Hours written 1-5 with no AM/PM in the source data are always PM
PM_HOURS_WITHOUT_MERIDIEM = {1, 2, 3, 4, 5}

# Manual corrections for names
NAME_ALIASES = {
    "md. eliaz": "Md.Eliaz",
    "md.eliaz": "Md.Eliaz",
}

# Subject abbreviations mapping
SUBJECT_ALIASES = {
    "dbms": "Data Base Management Systems",
    "dbms lab": "Data Base Management Systems Lab",
    "nlp": "Natural Language Processing",
    "dl": "Deep Learning",
    "dl lab": "Deep Learning Lab",
    "ml": "Machine Learning",
    "dlco": "Digital Logic and Computer Organization",
    "dl&co": "Digital Logic and Computer Organization",
    "ps": "Probability and Statistics",
    "stm": "Software Testing Methodology",
    "spm": "Software Project Management",
    "ipr": "Technical Paper Writing and IPR",
}

EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "mistral"
CHROMA_DB_PATH = "chroma_db"
CHROMA_COLLECTION_NAME = "department_data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("department_assistant")


# =====================================================================
# OPTIONAL DEPENDENCIES (LLM fallback + voice)
# =====================================================================

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("ollama not installed - LLM fallback disabled.")

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed - LLM fallback disabled.")

try:
    import win32com.client
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("win32com.client not installed - native text-to-speech disabled.")

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    logger.warning("speech_recognition not installed - voice input disabled.")


# =====================================================================
# DATA LOADING
# =====================================================================


def _strip_string_columns(df):
    for col in df.columns:
        try:
            df[col] = df[col].str.strip()
        except (AttributeError, TypeError):
            pass
    return df


def _apply_name_aliases(name):
    if not isinstance(name, str):
        return name
    return NAME_ALIASES.get(name.lower(), name)


def load_data(faculty_path=FACULTY_CSV_PATH, timetable_path=TIMETABLE_CSV_PATH):
    """Load and normalize the faculty and timetable CSVs."""
    try:
        faculty_df = pd.read_csv(faculty_path)
        timetable_df = pd.read_csv(timetable_path)
    except FileNotFoundError as e:
        logger.error("Could not find a required data file: %s", e)
        raise

    faculty_df.columns = faculty_df.columns.str.strip()
    timetable_df.columns = timetable_df.columns.str.strip()

    faculty_df = _strip_string_columns(faculty_df)
    timetable_df = _strip_string_columns(timetable_df)

    if "faculty_name" in faculty_df.columns:
        faculty_df["faculty_name"] = faculty_df["faculty_name"].apply(_apply_name_aliases)
    if "faculty" in timetable_df.columns:
        timetable_df["faculty"] = timetable_df["faculty"].apply(_apply_name_aliases)

    return faculty_df, timetable_df


faculty, timetable = load_data()
HAS_FACULTY_ID = "faculty_id" in faculty.columns


# -----------------------------
# CHROMADB (optional)
# -----------------------------

collection = None
if CHROMADB_AVAILABLE:
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception as e:
        logger.warning("Could not load ChromaDB collection '%s': %s", CHROMA_COLLECTION_NAME, e)
        collection = None


# =====================================================================
# TIME UTILITIES
# =====================================================================


def convert_college_time(time_str):
    hour, minute = map(int, str(time_str).strip().split(":"))
    if hour in PM_HOURS_WITHOUT_MERIDIEM:
        hour += 12
    return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()


def parse_time_from_text(time_match):
    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    meridiem = (time_match.group(3) or "").lower() or None

    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    elif meridiem is None and hour in PM_HOURS_WITHOUT_MERIDIEM:
        hour += 12

    try:
        return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    except ValueError:
        return None


def is_college_working_hours():
    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    if current_day not in WORKING_DAYS:
        return False, "Today is Sunday! College is closed."

    start_working = datetime.strptime(COLLEGE_START_TIME, "%H:%M").time()
    end_working = datetime.strptime(COLLEGE_END_TIME, "%H:%M").time()

    if current_time < start_working:
        return False, "College hasn't started yet today. It opens at 9:00 AM."
    elif current_time > end_working:
        return (
            False,
            f"College hours have ended for today (ended at 4:30 PM). "
            f"Current time is {now.strftime('%I:%M %p')}.",
        )

    return True, "Success"


def get_tomorrow_day():
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%A")


# =====================================================================
# NAME MATCHING HELPER
# =====================================================================


def _all_known_faculty_names():
    names = set(faculty["faculty_name"].dropna().unique())
    names.update(timetable["faculty"].dropna().unique())
    return names


def _drop_redundant_substring_matches(names):
    if len(names) <= 1:
        return names

    cores = {n: n.lower().rsplit(".", 1)[-1].strip() for n in names}
    keep = []
    for n, core in cores.items():
        is_redundant = any(
            core != other_core and core in other_core
            for other_n, other_core in cores.items()
            if other_n != n
        )
        if not is_redundant:
            keep.append(n)
    return keep if keep else names


def find_matching_faculty_names(query, known_names=None):
    if known_names is None:
        known_names = _all_known_faculty_names()

    query = query.strip().lower()
    if not query:
        return []

    exact = [n for n in known_names if n.lower() == query]
    if exact:
        return exact

    substring = [n for n in known_names if query in n.lower()]
    if substring:
        return substring

    full_name_hits = [n for n in known_names if n.lower() in query]
    if full_name_hits:
        return _drop_redundant_substring_matches(full_name_hits)

    core_matches = []
    for n in known_names:
        core = n.lower().rsplit(".", 1)[-1].strip()
        if query in core or core in query:
            core_matches.append(n)
    if core_matches:
        return _drop_redundant_substring_matches(core_matches)

    name_lookup = {}
    for n in known_names:
        core = n.lower().rsplit(".", 1)[-1].strip()
        name_lookup[core] = n
        name_lookup[n.lower()] = n

    fuzzy_matches = set()
    for word in re.findall(r"[a-z]+", query):
        if len(word) < 4:
            continue
        close = difflib.get_close_matches(word, name_lookup.keys(), n=2, cutoff=0.75)
        for c in close:
            fuzzy_matches.add(name_lookup[c])

    return list(fuzzy_matches)


# =====================================================================
# FACULTY STATUS (FREE / BUSY)
# =====================================================================


def get_free_faculty():
    is_working, message = is_college_working_hours()
    if not is_working:
        return message

    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    all_faculty = set(faculty["faculty_name"].dropna().unique())
    all_faculty.update(timetable["faculty"].dropna().unique())

    busy_faculty = set()

    for _, row in timetable.iterrows():
        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError) as e:
            logger.debug("Skipping unparsable timetable row %s: %s", row.to_dict(), e)
            continue

        if str(row["day"]).lower() == current_day and start <= current_time < end:
            if pd.notna(row["faculty"]):
                busy_faculty.add(row["faculty"])

    free_faculty = all_faculty - busy_faculty

    if not free_faculty:
        return "All faculty members are currently busy in classes right now."

    return (
        "Here are the faculty members free right now:\n* "
        + "\n* ".join(sorted(free_faculty))
    )


def get_faculty_free_status(name_query):
    is_working, message = is_college_working_hours()
    if not is_working:
        return message

    matches = find_matching_faculty_names(name_query)
    if not matches:
        return f"I couldn't find a faculty member matching '{name_query}'."
    if len(matches) > 1:
        return (
            f"That matches more than one person: {', '.join(sorted(matches))}. "
            "Could you be more specific?"
        )

    target_name = matches[0]

    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    for _, row in timetable.iterrows():
        if row["faculty"] != target_name:
            continue
        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError):
            continue

        if str(row["day"]).lower() == current_day and start <= current_time < end:
            return (
                f"{target_name} is currently busy: teaching {row['subject']} "
                f"to {row['section']} in {row['room_number']} "
                f"({row['starting_time']} - {row['ending_time']})."
            )

    return f"{target_name} is free right now."


# =====================================================================
# FACULTY ID SEARCH
# =====================================================================


def get_faculty_by_id(fid):
    if not HAS_FACULTY_ID:
        return (
            "Sorry, faculty ID lookup isn't available right now - the "
            "faculty data doesn't include an ID column. You can ask me "
            "for a faculty member by name instead."
        )

    rows = faculty[faculty["faculty_id"].astype(str).str.upper() == fid.upper()]

    if rows.empty:
        return f"No faculty member found with ID {fid}."

    row = rows.iloc[0]

    return f"""
Faculty Name : {row.get('faculty_name', 'N/A')}
Faculty ID   : {row.get('faculty_id', 'N/A')}
Designation  : {row.get('faculty_designation', 'N/A')}
Qualification: {row.get('faculty_qualification', 'N/A')}
Joining Date : {row.get('date_of_joining', 'N/A')}
Experience   : {row.get('experience_in_months', 'N/A')}
"""


def get_faculty_by_name(name_query):
    known_names = set(faculty["faculty_name"].dropna().unique())
    matches = find_matching_faculty_names(name_query, known_names=known_names)

    if not matches:
        return None

    if len(matches) > 1:
        return f"Multiple matches found: {', '.join(sorted(matches))}. Please be more specific."

    row = faculty[faculty["faculty_name"] == matches[0]].iloc[0]
    details = [f"Faculty Name : {row['faculty_name']}"]
    for label, col in [
        ("Designation", "faculty_designation"),
        ("Qualification", "faculty_qualification"),
        ("Joining Date", "date_of_joining"),
        ("Experience", "experience_in_months"),
    ]:
        if col in row and pd.notna(row[col]):
            details.append(f"{label:13}: {row[col]}")

    return "\n".join(details)


# =====================================================================
# FACULTY SUBJECTS
# =====================================================================


def get_subjects_by_faculty(question):
    q = question.lower()
    candidate_names = sorted(
        timetable["faculty"].dropna().unique(), key=len, reverse=True
    )

    for faculty_name in candidate_names:
        if str(faculty_name).lower() in q:
            rows = timetable[timetable["faculty"] == faculty_name]
            subjects = rows["subject"].unique()
            return f"{faculty_name} teaches:\n* " + "\n* ".join(subjects)

    matches = []
    for faculty_name in candidate_names:
        core = str(faculty_name).lower().rsplit(".", 1)[-1].strip()
        if core and re.search(rf"\b{re.escape(core)}\b", q):
            matches.append(faculty_name)

    if len(matches) == 1:
        rows = timetable[timetable["faculty"] == matches[0]]
        subjects = rows["subject"].unique()
        return f"{matches[0]} teaches:\n* " + "\n* ".join(subjects)
    elif len(matches) > 1:
        return (
            f"That name matches more than one faculty member: "
            f"{', '.join(sorted(matches))}. Could you be more specific "
            f"(e.g. include their initial)?"
        )

    return None


# =====================================================================
# DAY TIMETABLE
# =====================================================================


def get_day_timetable(section_name, day_name):
    rows = timetable[
        (timetable["section"] == section_name)
        & (timetable["day"].str.lower() == day_name.lower())
    ]

    if rows.empty:
        return f"No timetable found for {section_name} on {day_name}.\n"

    rows = rows.sort_values(by=["period"])

    answer = f"\n===== {section_name} =====\n"
    answer += f"{day_name.upper()}\n"

    for _, row in rows.iterrows():
        answer += (
            f"P{row['period']} - "
            f"{row['subject']} "
            f"({row['starting_time']} - {row['ending_time']}) | "
            f"Room: {row['room_number']} | Faculty: {row['faculty']}\n"
        )

    return answer


def get_first_or_last_class(section_name, day_name, which="first"):
    rows = timetable[
        (timetable["section"] == section_name)
        & (timetable["day"].str.lower() == day_name.lower())
    ]

    if rows.empty:
        return f"No timetable found for {section_name} on {day_name}.\n"

    rows = rows.sort_values(by=["period"])
    row = rows.iloc[0] if which == "first" else rows.iloc[-1]

    label = "first" if which == "first" else "last"
    return (
        f"The {label} class on {day_name.capitalize()} for {section_name} is "
        f"{row['subject']} (P{row['period']}, {row['starting_time']} - {row['ending_time']}) "
        f"in {row['room_number']} with {row['faculty']}."
    )


# =====================================================================
# SUBJECT SCHEDULE
# =====================================================================


def _resolve_subject_alias(text):
    return SUBJECT_ALIASES.get(text.strip().lower(), text)


def _find_subject_in_text(q, candidate_subjects=None):
    if candidate_subjects is None:
        candidate_subjects = sorted(
            timetable["subject"].dropna().unique(), key=len, reverse=True
        )

    for subject in candidate_subjects:
        if str(subject).lower() in q:
            return subject

    for abbrev, full_name in sorted(SUBJECT_ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(rf"\b{re.escape(abbrev)}\b", q):
            return full_name

    return None


def get_subject_faculty(question):
    q = question.lower()
    subject = _find_subject_in_text(q)
    if subject is None:
        return None

    rows = timetable[timetable["subject"].str.lower() == str(subject).lower()]
    faculty_names = sorted(rows["faculty"].dropna().unique())

    if not faculty_names:
        return f"I couldn't find who teaches {subject}."

    if len(faculty_names) == 1:
        return f"{faculty_names[0]} teaches {subject}."

    return f"{subject} is taught by: " + ", ".join(faculty_names)


def get_subject_current_room(question):
    q = question.lower()
    subject = _find_subject_in_text(q)
    if subject is None:
        return None

    is_working, message = is_college_working_hours()
    if not is_working:
        return message

    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    rows = timetable[timetable["subject"].str.lower() == str(subject).lower()]

    for _, row in rows.iterrows():
        if str(row["day"]).lower() != current_day:
            continue
        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError):
            continue
        if start <= current_time < end:
            return (
                f"{subject} is happening right now in {row['room_number']} "
                f"({row['section']}, taught by {row['faculty']}, "
                f"{row['starting_time']} - {row['ending_time']})."
            )

    return (
        f"{subject} isn't being taught right now. "
        f"Ask me for its full schedule if you'd like to know when/where it runs."
    )


def get_subject_schedule(question):
    q = question.lower()
    subject = _find_subject_in_text(q)
    if subject is None:
        return None

    rows = timetable[timetable["subject"].str.lower() == str(subject).lower()]
    answer = f"\n{subject} Schedule\n"

    for _, row in rows.iterrows():
        answer += (
            f"\nSection : {row['section']}"
            f"\nDay     : {row['day']}"
            f"\nPeriod  : {row['period']}"
            f"\nTime    : {row['starting_time']} - {row['ending_time']}\n"
        )

    return answer


# =====================================================================
# YEAR TIMETABLE
# =====================================================================


def get_sections_for_year(year):
    if year == "2":
        return ["CSM-2"]
    elif year == "3":
        return ["CSM-3A", "CSM-3B"]
    return None


def get_year_timetable(year):
    sections = get_sections_for_year(year)
    if sections is None:
        return "Year not found."

    rows = timetable[timetable["section"].isin(sections)].copy()
    rows["day_order"] = rows["day"].str.lower().map(DAY_ORDER)
    rows = rows.sort_values(by=["section", "day_order", "period"])

    answer = ""
    for section in sections:
        answer += f"\n===== {section} =====\n"
        sec_rows = rows[rows["section"] == section]
        current_day = ""

        for _, row in sec_rows.iterrows():
            if current_day != row["day"]:
                current_day = row["day"]
                answer += f"\n{current_day.upper()}\n"

            answer += (
                f"P{row['period']} - "
                f"{row['subject']} "
                f"({row['starting_time']} - {row['ending_time']}) | "
                f"Room: {row['room_number']} | Faculty: {row['faculty']}\n"
            )

    return answer


# =====================================================================
# CURRENT ROOM STATUS
# =====================================================================


def get_current_room(room):
    is_working, message = is_college_working_hours()
    if not is_working:
        return message

    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    for _, row in timetable.iterrows():
        if str(row["room_number"]).upper() != room.upper():
            continue

        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError):
            continue

        if str(row["day"]).lower() == current_day and start <= current_time < end:
            return f"""
Room: {room}
Section: {row['section']}
Subject: {row['subject']}
Faculty: {row['faculty']}
Time: {row['starting_time']} - {row['ending_time']}
"""

    return f"No class running in room {room} right now."


def get_room_day_schedule(room, day_name=None):
    if day_name is None:
        day_name = datetime.now().strftime("%A")

    rows = timetable[
        (timetable["room_number"].str.upper() == room.upper())
        & (timetable["day"].str.lower() == day_name.lower())
    ]

    if rows.empty:
        return f"No classes are scheduled in room {room} on {day_name.capitalize()}."

    rows = rows.sort_values(by=["period"])
    answer = f"\nSchedule for Room {room} on {day_name.capitalize()}:\n"
    for _, row in rows.iterrows():
        answer += (
            f"P{row['period']} - {row['subject']} "
            f"({row['starting_time']} - {row['ending_time']}) | "
            f"Section: {row['section']} | Faculty: {row['faculty']}\n"
        )

    return answer


# =====================================================================
# ROOM STATUS AT SPECIFIC TIME
# =====================================================================

TIME_PATTERN = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)?")
DAY_PATTERN_PARTS = "|".join(WORKING_DAYS)


def _extract_day(q):
    for day in WORKING_DAYS:
        if day in q:
            return day
    return None


def get_classes_at_period(period, day_name):
    rows = timetable[
        (timetable["period"] == period)
        & (timetable["day"].str.lower() == day_name.lower())
    ]

    if rows.empty:
        return f"No class found for period {period} on {day_name.capitalize()}."

    answer = f"Period {period} on {day_name.capitalize()}:\n"
    for _, row in rows.iterrows():
        answer += (
            f"* {row['section']}: {row['subject']} "
            f"({row['starting_time']} - {row['ending_time']}) | "
            f"Room: {row['room_number']} | Faculty: {row['faculty']}\n"
        )

    return answer


def get_faculty_with_most_subjects():
    counts = timetable.groupby("faculty")["subject"].nunique().sort_values(ascending=False)
    if counts.empty:
        return "I couldn't find subject data to answer that."

    top_count = counts.iloc[0]
    top_faculty = counts[counts == top_count].index.tolist()

    if len(top_faculty) == 1:
        return f"{top_faculty[0]} teaches the most subjects, with {top_count} distinct subjects."
    return (
        f"There's a tie: {', '.join(sorted(top_faculty))} each teach "
        f"{top_count} distinct subjects - the most of anyone."
    )


def get_most_used_room():
    counts = timetable["room_number"].value_counts()
    if counts.empty:
        return "I couldn't find room data to answer that."

    top_count = counts.iloc[0]
    top_rooms = counts[counts == top_count].index.tolist()

    if len(top_rooms) == 1:
        return f"{top_rooms[0]} is the most-used room, with {top_count} periods scheduled across the week."
    return (
        f"There's a tie: {', '.join(sorted(top_rooms))} are each used for "
        f"{top_count} periods across the week - the most of any room."
    )


def get_faculty_teaching_theory_and_lab():
    df = timetable.dropna(subset=["faculty", "subject"]).copy()
    df["is_lab"] = df["subject"].str.lower().str.contains("lab")

    grouped = df.groupby("faculty")["is_lab"].agg(["any", "all"])
    both = grouped[(grouped["any"]) & (~grouped["all"])]

    if both.empty:
        return "I couldn't find any faculty member who teaches both theory and lab subjects."

    names = sorted(both.index.tolist())
    return "Faculty who teach both theory and lab subjects:\n* " + "\n* ".join(names)


def get_room_status_at_time(question, room_number):
    q = question.lower()
    target_day = _extract_day(q)

    time_match = TIME_PATTERN.search(q)
    if not time_match:
        return get_current_room(room_number)

    target_time = parse_time_from_text(time_match)
    if target_time is None:
        return "Sorry, I couldn't understand that time. Try something like '2:30 pm'."

    matching_classes = []
    for _, row in timetable.iterrows():
        if str(row["room_number"]).upper() != room_number.upper():
            continue

        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError):
            continue

        if start <= target_time < end:
            row_day = str(row["day"]).lower()
            if target_day is None or row_day == target_day:
                matching_classes.append(row)

    time_str = time_match.group(0).strip()

    if target_day:
        if not matching_classes:
            return (
                f"No class scheduled in room {room_number} at {time_str} "
                f"on {target_day.capitalize()}."
            )

        row = matching_classes[0]
        return f"""
Room {room_number} Schedule details on {row['day']}:
Time Slot: {row['starting_time']} - {row['ending_time']} (Period P{row['period']})
Section  : {row['section']}
Subject  : {row['subject']}
Faculty  : {row['faculty']}
"""
    else:
        if not matching_classes:
            return f"No class scheduled in room {room_number} at {time_str} on any working day."

        answer = f"Schedule for Room {room_number} at {time_str} across the week:\n"
        matching_classes.sort(key=lambda r: DAY_ORDER.get(str(r["day"]).lower(), 7))

        for row in matching_classes:
            answer += (
                f"\n* {row['day']} (P{row['period']} | {row['starting_time']} - "
                f"{row['ending_time']}): {row['subject']} for {row['section']} by {row['faculty']}"
            )
        return answer


# =====================================================================
# ALL CLASSES AT SPECIFIC TIME
# =====================================================================


def _extract_section_filter(q):
    if "second year" in q or "2nd year" in q or "csm-2" in q:
        return ["CSM-2"]
    if "third year" in q or "3rd year" in q:
        if "section a" in q or "3a" in q:
            return ["CSM-3A"]
        elif "section b" in q or "3b" in q:
            return ["CSM-3B"]
        return ["CSM-3A", "CSM-3B"]
    return None


def get_classes_at_time(question):
    q = question.lower()
    section_filter = _extract_section_filter(q)
    target_day = _extract_day(q) or datetime.now().strftime("%A").lower()

    time_match = TIME_PATTERN.search(q)
    if not time_match:
        return "Please provide a valid time (e.g., 9:30)."

    target_time = parse_time_from_text(time_match)
    if target_time is None:
        return "Sorry, I couldn't understand that time. Try something like '9:30 am'."

    df = timetable[timetable["day"].str.lower() == target_day]
    if section_filter:
        df = df[df["section"].isin(section_filter)]

    active_classes = []
    for _, row in df.iterrows():
        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError):
            continue

        if start <= target_time < end:
            active_classes.append(
                f"* P{row['period']} ({row['starting_time']} - {row['ending_time']}): "
                f"{row['subject']} ({row['section']}) | Room: {row['room_number']} | "
                f"Faculty: {row['faculty']}"
            )

    if not active_classes:
        return (
            f"No classes found for the specified criteria at "
            f"{time_match.group(0)} on {target_day.capitalize()}."
        )

    return (
        f"Classes found at {time_match.group(0)} on {target_day.capitalize()}:\n\n"
        + "\n".join(active_classes)
    )


# =====================================================================
# CURRENT YEAR CLASS
# =====================================================================


def get_current_year_class(year):
    is_working, message = is_college_working_hours()
    if not is_working:
        return message

    sections = get_sections_for_year(year)
    if sections is None:
        return "Year not found."

    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    rows = timetable[timetable["section"].isin(sections)]
    active_classes = []

    for _, row in rows.iterrows():
        try:
            start = convert_college_time(row["starting_time"])
            end = convert_college_time(row["ending_time"])
        except (ValueError, TypeError):
            continue

            active_classes.append(f"""
Section : {row['section']}
Subject : {row['subject']}
Faculty : {row['faculty']}
Room    : {row['room_number']}
Time    : {row['starting_time']} - {row['ending_time']}""")

    if active_classes:
        return "\nActive Current Classes:\n" + "\n---\n".join(active_classes)

    return "No class is running currently right now."


def get_next_class_for_section(section_name):
    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.time()

    rows = timetable[
        (timetable["section"] == section_name)
        & (timetable["day"].str.lower() == current_day)
    ]

    upcoming = []
    for _, row in rows.iterrows():
        try:
            start = convert_college_time(row["starting_time"])
        except (ValueError, TypeError):
            continue
        if start > current_time:
            upcoming.append((start, row))

    if not upcoming:
        return None

    upcoming.sort(key=lambda pair: pair[0])
    _, next_row = upcoming[0]
    return next_row


def get_next_class(year):
    is_working, message = is_college_working_hours()
    if not is_working:
        return message

    sections = get_sections_for_year(year)
    if sections is None:
        return "Year not found."

    answers = []
    for section in sections:
        next_row = get_next_class_for_section(section)
        if next_row is None:
            answers.append(f"{section}: No more classes scheduled for today.")
        else:
            answers.append(
                f"{section}: Next up is {next_row['subject']} "
                f"(P{next_row['period']}, {next_row['starting_time']} - {next_row['ending_time']}) "
                f"in {next_row['room_number']} with {next_row['faculty']}."
            )

    return "\n".join(answers)


# =====================================================================
# LLM FALLBACK (OLLAMA + CHROMADB)
# =====================================================================


def get_llm_fallback_answer(question):
    if not (OLLAMA_AVAILABLE and CHROMADB_AVAILABLE and collection is not None):
        return (
            "I couldn't find a direct answer to that in the timetable or "
            "faculty data, and the AI fallback isn't configured right now. "
            "Try rephrasing your question, e.g. asking about a specific "
            "faculty member, subject, room, or day."
        )

    try:
        embedding = ollama.embeddings(model=EMBEDDING_MODEL, prompt=question)["embedding"]
        results = collection.query(query_embeddings=[embedding], n_results=10)
        context = "\n".join(results["documents"][0])

        prompt = f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:\n"
        response = ollama.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]
    except Exception as e:
        logger.error("LLM fallback failed: %s", e)
        return (
            "I couldn't find a direct answer to that, and the AI fallback "
            "ran into an error. Please try rephrasing your question."
        )


# =====================================================================
# MAIN ASSISTANT ROUTER
# =====================================================================


def ask_assistant(question):
    if not question or not question.strip():
        return "Please ask a question."

    q = re.sub(r"\s+", " ", question.lower().strip())

    status_trigger_words = [
        "free", "available", "busy",
        "have class", "having class", "has class",
        "in class", "is teaching", "teaching now", "teaching right now",
    ]
    mentions_room = re.search(r"\bT\d+\b", question.upper()) is not None

    if not mentions_room and any(word in q for word in status_trigger_words):
        known_names = _all_known_faculty_names()
        named_matches = find_matching_faculty_names(q, known_names=known_names)
        named_matches = [m for m in named_matches if len(m) > 3]

        if named_matches and len(named_matches) <= 2:
            if len(named_matches) == 1:
                return get_faculty_free_status(named_matches[0])
            return (
                f"That name matches more than one faculty member: "
                f"{', '.join(sorted(named_matches))}. Could you be more specific?"
            )

        generic_free_pattern = re.compile(
            r"\b(faculty|teacher|staff|anyone|professor|who)\b"
        )
        if generic_free_pattern.search(q):
            return get_free_faculty()

    id_match = re.search(r"TS_[A-Z]+_\d+", question.upper())
    if id_match:
        return get_faculty_by_id(id_match.group())

    profile_keyword_pattern = re.search(
        r"who is|about faculty|profile of|qualification|experience|"
        r"designation|joining|details? of|info(?:rmation)? (?:about|on)|"
        r"faculty id|when did .* join",
        q,
    )
    if profile_keyword_pattern:
        known_names = set(faculty["faculty_name"].dropna().unique())
        name_matches = find_matching_faculty_names(q, known_names=known_names)
        name_matches = [m for m in name_matches if len(m) > 3]
        if len(name_matches) == 1:
            result = get_faculty_by_name(name_matches[0])
            if result:
                return result
        elif len(name_matches) > 1:
            return (
                f"That name matches more than one faculty member: "
                f"{', '.join(sorted(name_matches))}. Could you be more specific?"
            )

    if len(q.split()) <= 3:
        bare_name_result = get_faculty_by_name(q)
        if bare_name_result:
            return bare_name_result

    room_match = re.search(r"\bT\d+\b", question.upper())
    time_indicator_pattern = re.compile(
        r"\b(now|current|currently|going on|morning|evening|afternoon)\b"
    )

    if re.search(r"\d{1,2}:\d{2}", q):
        if room_match:
            return get_room_status_at_time(question, room_match.group())
        return get_classes_at_time(question)

    if room_match and time_indicator_pattern.search(q):
        return get_room_status_at_time(question, room_match.group())

    if room_match:
        named_day = _extract_day(q)
        if named_day or "today" in q or "scheduled" in q:
            return get_room_day_schedule(room_match.group(), named_day)
        return get_current_room(room_match.group())

    if re.search(r"(second|2nd|2)\s*year", q) and ("current" in q or "now" in q):
        return get_current_year_class("2")

    if re.search(r"(third|3rd|3)\s*year", q) and ("current" in q or "now" in q):
        return get_current_year_class("3")

    if "next class" in q or "next period" in q or "upcoming class" in q:
        if re.search(r"(second|2nd|2)\s*year", q) or "csm-2" in q:
            return get_next_class("2")
        if re.search(r"(third|3rd|3)\s*year", q) or "csm-3" in q:
            return get_next_class("3")

    who_teaches_pattern = re.search(
        r"who (?:is )?teach(?:es|ing)?|which faculty (?:teaches|handles)|"
        r"who (?:is )?handling",
        q,
    )
    if who_teaches_pattern:
        result = get_subject_faculty(question)
        if result:
            return result

    which_room_pattern = re.search(
        r"which room (?:has|is)|where is .* (?:being )?(?:conducted|taught|happening|held)|"
        r"what room",
        q,
    )
    if which_room_pattern:
        result = get_subject_current_room(question)
        if result:
            return result

    result = get_subjects_by_faculty(question)
    if result:
        return result

    result = get_subject_schedule(question)
    if result:
        return result

    if re.search(r"most subjects|teaches the most", q):
        return get_faculty_with_most_subjects()
    if re.search(r"room is used most|most frequently used room|most used room", q):
        return get_most_used_room()
    if re.search(r"both theory and lab|theory and lab subjects", q):
        return get_faculty_teaching_theory_and_lab()

    period_match = re.search(r"period\s+(\d+)", q)
    if period_match:
        period_day = _extract_day(q)
        if period_day:
            return get_classes_at_period(int(period_match.group(1)), period_day)

    # Tomorrow timetable
    if "tomorrow" in q:
        tomorrow_day = get_tomorrow_day()

        if re.search(r"(second|2nd|2)\s*year", q) or "csm-2" in q:
            return get_day_timetable("CSM-2", tomorrow_day)

        if "section a" in q or "3a" in q:
            return get_day_timetable("CSM-3A", tomorrow_day)

        if "section b" in q or "3b" in q:
            return get_day_timetable("CSM-3B", tomorrow_day)

        if re.search(r"(third|3rd|3)\s*year", q):
            return (
                get_day_timetable("CSM-3A", tomorrow_day)
                + get_day_timetable("CSM-3B", tomorrow_day)
            )

    target_day = _extract_day(q)

    first_last_match = re.search(r"\b(first|last)\b", q)
    if target_day and first_last_match:
        which = first_last_match.group(1)
        if "csm-2" in q or re.search(r"(second|2nd|2)\s*year", q):
            return get_first_or_last_class("CSM-2", target_day.capitalize(), which)
        if "csm-3a" in q or "section a" in q or "3a" in q:
            return get_first_or_last_class("CSM-3A", target_day.capitalize(), which)
        if "csm-3b" in q or "section b" in q or "3b" in q:
            return get_first_or_last_class("CSM-3B", target_day.capitalize(), which)

    if target_day:
        if "section a" in q or "3a" in q:
            return get_day_timetable("CSM-3A", target_day.capitalize())
        if "section b" in q or "3b" in q:
            return get_day_timetable("CSM-3B", target_day.capitalize())
        if re.search(r"(third|3rd|3)\s*year", q):
            return get_day_timetable("CSM-3A", target_day.capitalize()) + get_day_timetable(
                "CSM-3B", target_day.capitalize()
            )
        if re.search(r"(second|2nd|2)\s*year", q) or "csm-2" in q:
            return get_day_timetable("CSM-2", target_day.capitalize())
    
    if re.search(r"(second|2nd|2)\s*year", q) or "csm-2" in q:
        return get_year_timetable("2")

    if re.search(r"(third|3rd|3)\s*year", q):
        return get_year_timetable("3")

    return get_llm_fallback_answer(question)


# =====================================================================
# VOICE UTILITIES (NATIVE SAPI WINDOWS + WHISPER)
# =====================================================================

_tts_engine = None
if TTS_AVAILABLE:
    try:
        # Use native Windows speech dispatcher instead of pyttsx3
        _tts_engine = win32com.client.Dispatch("SAPI.SpVoice")
    except Exception as e:
        logger.warning("Native Windows TTS engine failed to initialize: %s", e)
        _tts_engine = None


def speak(text):
    """Converts a text string to local system output audio using Windows SAPI."""
    if _tts_engine is None:
        return
    clean_text = text.replace("*", "").replace("=", "").replace("---", "")
    try:
        _tts_engine.Speak(clean_text)
    except Exception as e:
        logger.warning("Native TTS playback failed: %s", e)


def listen_and_transcribe():
    """Captures microphone audio and transcribes locally using Whisper."""
    if not STT_AVAILABLE:
        print("Voice input isn't available (speech_recognition not installed).")
        return ""

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\nAdjusting for background noise... Please wait.")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening! Ask your question...")

            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            print("Processing speech with local Whisper...")

            text = recognizer.recognize_whisper(audio, model="base", language="english")
            return text.strip()

    except sr.WaitTimeoutError:
        print("No speech detected.")
        return ""
    except sr.UnknownValueError:
        print("Whisper could not interpret the input audio.")
        return ""
    except OSError as e:
        print(f"Microphone unavailable: {e}")
        return ""
    except Exception as e:
        logger.error("Voice input failed: %s", e)
        return ""


# =====================================================================
# INTERACTIVE TERMINAL LOOP
# =====================================================================


def main():
    print("=====================================================")
    print("Welcome to the Voice-Enabled Department Assistant!")
    print("Type 'exit' or 'quit' to stop.")
    if STT_AVAILABLE:
        print("Press 'Enter' with an empty prompt to use your Voice.")
    print("=====================================================\n")

    while True:
        try:
            user_input = input("Ask your question (or press Enter to speak): ")

            if user_input.strip().lower() in ["exit", "quit"]:
                print("Goodbye!")
                speak("Goodbye! Have a great day.")
                break

            if not user_input.strip():
                user_question = listen_and_transcribe()
                if not user_question:
                    continue
                print(f"You asked: {user_question}")
            else:
                user_question = user_input

            response = ask_assistant(user_question)

            print("\nAnswer:")
            print(response)
            print("-" * 40 + "\n")

            speak(response)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            speak("Goodbye!")
            break
        except Exception as e:
            logger.exception("Unexpected error while handling a question")
            print(f"\nAn error occurred: {e}\n")
            speak("Sorry, an error occurred while processing your request.")


if __name__ == "__main__":
    main()