import psycopg2
from datetime import datetime

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
# Current Day & Time
# -----------------------------
def get_current_day_time():
    now = datetime.now()
    day = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    return day, current_time


# -----------------------------
# SECTION TIMETABLE
# -----------------------------
def get_section_timetable(section):

    cur.execute("""
        SELECT
            day,
            period,
            subject,
            faculty,
            starting_time,
            ending_time,
            room_number
        FROM time_table
        WHERE LOWER(section)=LOWER(%s)
        ORDER BY
            CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
            END,
            period::int
    """, (section,))

    return cur.fetchall()


# -----------------------------
# CURRENT CLASS
# -----------------------------
def get_current_class():

    day, current_time = get_current_day_time()

    cur.execute("""
        SELECT
            faculty,
            subject,
            section,
            room_number,
            starting_time,
            ending_time
        FROM time_table
        WHERE day=%s
        AND %s BETWEEN starting_time AND ending_time
    """, (day, current_time))

    return cur.fetchall()


# -----------------------------
# VACANT ROOMS
# -----------------------------
def get_vacant_rooms():

    day, current_time = get_current_day_time()

    cur.execute("SELECT DISTINCT room_number FROM time_table")
    all_rooms = {row[0] for row in cur.fetchall()}

    cur.execute("""
        SELECT DISTINCT room_number
        FROM time_table
        WHERE day=%s
        AND %s BETWEEN starting_time AND ending_time
    """, (day, current_time))

    occupied_rooms = {row[0] for row in cur.fetchall()}

    return sorted(list(all_rooms - occupied_rooms))


# -----------------------------
# NEXT CLASS
# -----------------------------
def get_next_class(section):

    day, current_time = get_current_day_time()

    cur.execute("""
        SELECT
            subject,
            faculty,
            room_number,
            starting_time,
            ending_time,
            period
        FROM time_table
        WHERE LOWER(section)=LOWER(%s)
        AND day=%s
        AND starting_time > %s
        ORDER BY starting_time
        LIMIT 1
    """, (section, day, current_time))

    return cur.fetchone()


# =========================================================
#   NEW ADDITIONS (STEP 4 SERVICES)
# =========================================================


# -----------------------------
# ROOM STATUS (NOW IN A ROOM)
# -----------------------------
def get_room_status(room):

    day, current_time = get_current_day_time()

    cur.execute("""
        SELECT
            faculty,
            subject,
            section,
            period,
            starting_time,
            ending_time
        FROM time_table
        WHERE room_number=%s
        AND day=%s
        AND %s BETWEEN starting_time AND ending_time
    """, (room, day, current_time))

    return cur.fetchall()


# -----------------------------
# DAY TIMETABLE (SECTION + DAY)
# -----------------------------
def get_day_timetable(section, day):

    cur.execute("""
        SELECT
            period,
            subject,
            faculty,
            room_number,
            starting_time,
            ending_time
        FROM time_table
        WHERE LOWER(section)=LOWER(%s)
        AND LOWER(day)=LOWER(%s)
        ORDER BY period::int
    """, (section, day))

    return cur.fetchall()


# -----------------------------
# FIRST CLASS OF DAY
# -----------------------------
def get_first_class(section, day):

    cur.execute("""
        SELECT
            period,
            subject,
            faculty,
            room_number,
            starting_time,
            ending_time
        FROM time_table
        WHERE LOWER(section)=LOWER(%s)
        AND LOWER(day)=LOWER(%s)
        ORDER BY period::int ASC
        LIMIT 1
    """, (section, day))

    return cur.fetchone()


# -----------------------------
# LAST CLASS OF DAY
# -----------------------------
def get_last_class(section, day):

    cur.execute("""
        SELECT
            period,
            subject,
            faculty,
            room_number,
            starting_time,
            ending_time
        FROM time_table
        WHERE LOWER(section)=LOWER(%s)
        AND LOWER(day)=LOWER(%s)
        ORDER BY period::int DESC
        LIMIT 1
    """, (section, day))

    return cur.fetchone()

# -----------------------------
# CLASS BY TIME
# -----------------------------
def normalize_time_numbers(query):

    import re

    def convert(match):

        num = match.group()

        if len(num) == 4:
            return f"{num[:2]}.{num[2:]}"

        elif len(num) == 3:
            return f"{num[0]}.{num[1:]}"

        return num

    return re.sub(r"\b\d{3,4}\b", convert, query)

def get_class_by_time(query, section, day):

    import re

    query = normalize_time_numbers(query)

    match = re.search(
        r'(\d{1,2}[.:]\d{2})',
        query
    )

    if not match:
        return None

    query_time = match.group(1).replace(".", ":")

    hour, minute = query_time.split(":")
    query_time = f"{int(hour):02d}:{minute}"


    cur.execute("""
        SELECT
            period,
            subject,
            faculty,
            room_number,
            starting_time,
            ending_time
        FROM time_table
        WHERE LOWER(section)=LOWER(%s)
        AND LOWER(day)=LOWER(%s)
        AND %s::time >= starting_time::time
        AND %s::time < ending_time::time
        LIMIT 1
    """, (
        section,
        day,
        query_time,
        query_time
    ))


    result = cur.fetchone()

    return result 

# -----------------------------
# ROOM SCHEDULE
# -----------------------------
def get_room_schedule(room, day):

    cur.execute("""
        SELECT
            period,
            subject,
            faculty,
            section,
            room_number,
            starting_time,
            ending_time
        FROM time_table
        WHERE room_number=%s
        AND LOWER(day)=LOWER(%s)
        ORDER BY period::int
    """, (room, day))

    return cur.fetchall()