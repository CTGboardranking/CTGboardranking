import json
import os
from collections import defaultdict


# ============================================================
# FILES
# ============================================================

INSTITUTION_FILE = "institution-collector/institution_results.json"
STUDENT_FILE = "scraper/students.json"

OUTPUT_DIR = "data"

MERGED_STUDENT_FILE = os.path.join(
    OUTPUT_DIR,
    "merged_students.json"
)

STUDENT_RANKING_FILE = os.path.join(
    OUTPUT_DIR,
    "student_ranking.json"
)

INSTITUTION_RANKING_FILE = os.path.join(
    OUTPUT_DIR,
    "institution_ranking.json"
)

DISTRICT_RANKING_FILE = os.path.join(
    OUTPUT_DIR,
    "district_ranking.json"
)

SUMMARY_FILE = os.path.join(
    OUTPUT_DIR,
    "ranking_summary.json"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        print(f"WARNING: File not found: {filename}")
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(f"ERROR loading {filename}: {e}")
        return default


def save_json(filename, data):

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True
    )

    temp_file = filename + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        filename
    )


def number(value, default=0):

    try:
        return float(value)
    except:
        return default


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 60)
print("SSC 2026 MERGE & RANK SYSTEM")
print("=" * 60)

institutions = load_json(
    INSTITUTION_FILE,
    []
)

students = load_json(
    STUDENT_FILE,
    []
)

print()
print("Institution records:", len(institutions))
print("Student records:", len(students))


# ============================================================
# MERGE STUDENTS WITH INSTITUTION DATA
# ============================================================

print()
print("=" * 60)
print("MERGING STUDENT + INSTITUTION DATA")
print("=" * 60)


# EIIN based institution lookup

institution_map = {}

for institution in institutions:

    eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()

    if eiin:
        institution_map[eiin] = institution


# Existing merged data

old_merged = load_json(
    MERGED_STUDENT_FILE,
    []
)

if not isinstance(
    old_merged,
    list
):

    old_merged = []


# Roll based storage

merged_map = {}


# Load previous data first

for student in old_merged:

    roll = str(
        student.get(
            "roll",
            ""
        )
    ).strip()

    if roll:
        merged_map[roll] = student


# Merge new students

for student in students:

    roll = str(
        student.get(
            "roll",
            ""
        )
    ).strip()

    if not roll:
        continue


    # Copy student data

    merged = dict(student)


    # --------------------------------------------------------
    # Find institution
    # --------------------------------------------------------

    eiin = str(
        student.get(
            "eiin",
            ""
        )
    ).strip()


    institution = None


    if eiin:

        institution = institution_map.get(
            eiin
        )


    # --------------------------------------------------------
    # Institution name matching fallback
    # --------------------------------------------------------

    if institution is None:

        student_institute = str(
            student.get(
                "institute",
                ""
            )
        ).strip().upper()


        if student_institute:

            for item in institutions:

                name = str(
                    item.get(
                        "institution_name",
                        ""
                    )
                ).strip().upper()


                if (
                    name
                    and
                    name == student_institute
                ):

                    institution = item
                    break


    # --------------------------------------------------------
    # Add institution information
    # --------------------------------------------------------

    if institution:

        merged["eiin"] = str(
            institution.get(
                "eiin",
                eiin
            )
        )

        merged["institution_name"] = (
            institution.get(
                "institution_name",
                student.get(
                    "institute",
                    ""
                )
            )
        )

        merged["district"] = (
            institution.get(
                "district",
                student.get(
                    "district",
                    ""
                )
            )
        )

        merged["thana"] = (
            institution.get(
                "thana",
                ""
            )
        )

        merged["institution_appeared"] = (
            institution.get(
                "appeared"
            )
        )

        merged["institution_passed"] = (
            institution.get(
                "passed"
            )
        )

        merged["institution_passing_rate"] = (
            institution.get(
                "passing_rate"
            )
        )

        merged["institution_gpa5"] = (
            institution.get(
                "gpa5"
            )
        )


    # Save/update by roll

    merged_map[roll] = merged


merged_students = list(
    merged_map.values()
)


# ============================================================
# SAVE MERGED DATA
# ============================================================

save_json(
    MERGED_STUDENT_FILE,
    merged_students
)

print(
    "Merged students:",
    len(merged_students)
)


# ============================================================
# STUDENT RANKING
# ============================================================

print()
print("=" * 60)
print("CREATING STUDENT RANKING")
print("=" * 60)


# Only students with valid GPA

rankable_students = []

for student in merged_students:

    gpa = student.get("gpa")

    if gpa is None:
        continue

    try:

        gpa = float(gpa)

    except:

        continue


    item = dict(student)

    item["gpa"] = gpa

    rankable_students.append(
        item
    )


# Sort:
# 1. GPA descending
# 2. Roll ascending

rankable_students.sort(
    key=lambda x: (
        -x["gpa"],
        str(x.get("roll", ""))
    )
)


student_ranking = []

previous_gpa = None
rank = 0

for position, student in enumerate(
    rankable_students,
    start=1
):

    gpa = student["gpa"]


    if gpa != previous_gpa:

        rank = position

        previous_gpa = gpa


    item = dict(student)

    item["rank"] = rank

    student_ranking.append(
        item
    )


save_json(
    STUDENT_RANKING_FILE,
    student_ranking
)


print(
    "Ranked students:",
    len(student_ranking)
)


# ============================================================
# INSTITUTION RANKING
# ============================================================

print()
print("=" * 60)
print("CREATING INSTITUTION RANKING")
print("=" * 60)


institution_ranking = []


for institution in institutions:

    item = dict(institution)


    appeared = number(
        institution.get(
            "appeared"
        )
    )

    passed = number(
        institution.get(
            "passed"
        )
    )

    gpa5 = number(
        institution.get(
            "gpa5"
        )
    )

    passing_rate = number(
        institution.get(
            "passing_rate"
        )
    )


    # --------------------------------------------------------
    # Ranking score
    # --------------------------------------------------------
    #
    # Primary:
    # Passing rate
    #
    # Secondary:
    # GPA-5
    #
    # Tertiary:
    # Passed students
    #

    item["_appeared"] = appeared
    item["_passed"] = passed
    item["_gpa5"] = gpa5
    item["_passing_rate"] = passing_rate


    institution_ranking.append(
        item
    )


institution_ranking.sort(
    key=lambda x: (
        -x["_passing_rate"],
        -x["_gpa5"],
        -x["_passed"]
    )
)


final_institution_ranking = []


for position, institution in enumerate(
    institution_ranking,
    start=1
):

    item = dict(institution)

    item["rank"] = position

    item.pop(
        "_appeared",
        None
    )

    item.pop(
        "_passed",
        None
    )

    item.pop(
        "_gpa5",
        None
    )

    item.pop(
        "_passing_rate",
        None
    )

    final_institution_ranking.append(
        item
    )


save_json(
    INSTITUTION_RANKING_FILE,
    final_institution_ranking
)


print(
    "Ranked institutions:",
    len(final_institution_ranking)
)


# ============================================================
# DISTRICT RANKING
# ============================================================

print()
print("=" * 60)
print("CREATING DISTRICT RANKING")
print("=" * 60)


districts = defaultdict(
    lambda: {
        "institutions": 0,
        "appeared": 0,
        "passed": 0,
        "gpa5": 0
    }
)


for institution in institutions:

    district = str(
        institution.get(
            "district",
            ""
        )
    ).strip()


    if not district:
        district = "Unknown"


    data = districts[district]


    data["institutions"] += 1

    data["appeared"] += int(
        number(
            institution.get(
                "appeared"
            )
        )
    )

    data["passed"] += int(
        number(
            institution.get(
                "passed"
            )
        )
    )

    data["gpa5"] += int(
        number(
            institution.get(
                "gpa5"
            )
        )
    )


district_ranking = []


for district, data in districts.items():

    appeared = data["appeared"]
    passed = data["passed"]


    if appeared > 0:

        passing_rate = (
            passed / appeared
        ) * 100

    else:

        passing_rate = 0


    district_ranking.append({

        "district": district,

        "institutions":
            data["institutions"],

        "appeared":
            appeared,

        "passed":
            passed,

        "passing_rate":
            round(
                passing_rate,
                2
            ),

        "gpa5":
            data["gpa5"]
    })


district_ranking.sort(
    key=lambda x: (
        -x["passing_rate"],
        -x["gpa5"],
        -x["passed"]
    )
)


for position, district in enumerate(
    district_ranking,
    start=1
):

    district["rank"] = position


save_json(
    DISTRICT_RANKING_FILE,
    district_ranking
)


print(
    "Ranked districts:",
    len(district_ranking)
)


# ============================================================
# SUMMARY
# ============================================================

summary = {

    "year": 2026,

    "board": "Chattogram Board",

    "institutions":
        len(institutions),

    "students":
        len(merged_students),

    "rankable_students":
        len(student_ranking),

    "districts":
        len(district_ranking),

    "files": {

        "merged_students":
            MERGED_STUDENT_FILE,

        "student_ranking":
            STUDENT_RANKING_FILE,

        "institution_ranking":
            INSTITUTION_RANKING_FILE,

        "district_ranking":
            DISTRICT_RANKING_FILE
    }
}


save_json(
    SUMMARY_FILE,
    summary
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 60)
print("MERGE & RANK COMPLETED")
print("=" * 60)

print(
    "Institutions:",
    len(institutions)
)

print(
    "Students:",
    len(merged_students)
)

print(
    "Student ranking:",
    len(student_ranking)
)

print(
    "Districts:",
    len(district_ranking)
)

print()
print("OUTPUT FILES:")
print(
    MERGED_STUDENT_FILE
)
print(
    STUDENT_RANKING_FILE
)
print(
    INSTITUTION_RANKING_FILE
)
print(
    DISTRICT_RANKING_FILE
)
print(
    SUMMARY_FILE
)

print("=" * 60)
