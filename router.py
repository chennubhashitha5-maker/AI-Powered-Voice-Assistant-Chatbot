from query_classifier import classify_query
from service_classifier import classify_service_query

from faculty_retriever import retrieve_faculty
from timetable_retriever import retrieve_timetable
from timetable_service import (
    get_section_timetable,
    get_current_class,
    get_vacant_rooms,
    get_next_class,
    get_room_status,
    get_day_timetable,
    get_first_class,
    get_last_class,
    get_class_by_time,
)

import re


def extract_section(query):

    q = query.upper()

    if re.search(
        r"(CSM[- ]?2|CSM2|SECOND CSM|2ND CSM|SECONDCSM|2NDCSM)",
        q
    ):
        return "CSM-2"

    if re.search(
        r"(CSM[- ]?3A|CSM3A|CSMA|3RD CSMA|THIRD CSMA|THIRD CSM A|3RD CSM A|THIRDCSMA|3RDCSMA)",
        q
    ):
        return "CSM-3A"

    if re.search(
        r"(CSM[- ]?3B|CSM3B|CSMB|3RD CSMB|THIRD CSMB|THIRD CSM B|3RD CSM B|THIRDCSMB|3RDCSMB)",
        q
    ):
        return "CSM-3B"

    return None


# -----------------------------
# ROUTER
# -----------------------------
def route_query(query):

    category = classify_query(query)
    print("\nQuery Category:", category)

    # -----------------------------
    # FACULTY FLOW
    # -----------------------------
    if "FACULTY" in category:

        docs = retrieve_faculty(query)
        if docs is None:
             return {
                "type": "UNKNOWN",
                "data": "none"
             }
        return {
            "type": "FACULTY",
            "data": docs
        }

    # -----------------------------
    # SERVICE CLASSIFICATION
    # -----------------------------
    service = classify_service_query(query)
    print("Service Category:", service)

    # -----------------------------
    # LOOKUP
    # -----------------------------
    if "LOOKUP" in service:

        return {
            "type": "LOOKUP",
            "data": retrieve_timetable(query)
        }

    # -----------------------------
    # SECTION TIMETABLE
    # -----------------------------
    if "SECTION_TIMETABLE" in service:

        section = extract_section(query)

        if not section:
            return {"type": "ERROR", "data": "Section not found"}

        return {
            "type": "SECTION_TIMETABLE",
            "data": get_section_timetable(section)
        }

    # -----------------------------
    # VACANT ROOMS
    # -----------------------------
    if "VACANT_ROOMS" in service:

        return {
            "type": "VACANT_ROOMS",
            "data": get_vacant_rooms()
        }

    # -----------------------------
    # NEXT CLASS
    # -----------------------------
    if "NEXT_CLASS" in service:

        section = extract_section(query)

        if not section:
            return {"type": "ERROR", "data": "Section not found"}

        return {
            "type": "NEXT_CLASS",
            "data": get_next_class(section)
        }

    # -----------------------------
    # ROOM STATUS (NEW)
    # -----------------------------
    if "ROOM_STATUS" in service:

        match = re.search(r"T\d+", query.upper())

        if not match:
            return {"type": "ERROR", "data": "Room not found"}

        return {
            "type": "ROOM_STATUS",
            "data": get_room_status(match.group())
        }

    # -----------------------------
    # DAY TIMETABLE (NEW)
    # -----------------------------
    if "DAY_TIMETABLE" in service:

        section = extract_section(query)

        day = re.search(
            r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY)",
            query.upper()
        )

        if not section or not day:
            return {"type": "ERROR", "data": "Missing section/day"}

        return {
            "type": "DAY_TIMETABLE",
            "data": get_day_timetable(section, day.group().capitalize())
        }
        
        
    # -----------------------------
    # FIRST CLASS
    # -----------------------------
    if "FIRST_CLASS" in service:

        section = extract_section(query)

        day = re.search(
            r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY)",
            query.upper()
        )

        if not section or not day:
            return {
                "type": "ERROR",
                "data": "Missing section/day"
            }

        return {
            "type": "FIRST_CLASS",
            "data": get_first_class(
                section,
                day.group().capitalize()
            )
        }


    # -----------------------------
    # LAST CLASS
    # -----------------------------
    if "LAST_CLASS" in service:

        section = extract_section(query)

        day = re.search(
            r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY)",
            query.upper()
        )

        if not section or not day:
            return {
                "type": "ERROR",
                "data": "Missing section/day"
            }

        return {
            "type": "LAST_CLASS",
            "data": get_last_class(
                section,
                day.group().capitalize()
            )
        } 


    # -----------------------------
    # CLASS BY TIME
    # -----------------------------
    if "CLASS_BY_TIME" in service:

        section = extract_section(query)

        day = re.search(
            r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY)",
            query.upper()
        )

        if not section or not day:
            return {
                "type": "ERROR",
                "data": "Missing section/day"
            }

        return {
            "type": "CLASS_BY_TIME",
            "data": get_class_by_time(
                query,
                section,
                day.group().capitalize()
            )
        }
        
    return {
        "type": "UNKNOWN",
        "data": None
    }
    