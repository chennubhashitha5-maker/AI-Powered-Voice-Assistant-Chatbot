from faculty_name_matcher import match_faculty_name

while True:

    query = input("\nName: ")

    result = match_faculty_name(query)

    print("Match:", result)