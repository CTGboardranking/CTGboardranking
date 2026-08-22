import json
import os
from collections import Counter


INPUT_FILE = "scraper/parsed_result.json"
OUTPUT_FILE = "scraper/institution_stats.json"


# ============================================================
# LOAD RESULT
# ============================================================

if not os.path.exists(INPUT_FILE):
    raise SystemExit(
        f"Input file not found: {INPUT_FILE}"
    )


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:
    result = json.load(f)


# ============================================================
# BASIC DATA
# ============================================================

institute = result.get(
    "institute",
    ""
).strip()

gpa = result.get(
    "gpa"
)

subjects = result.get(
    "subjects",
    [])


if not institute:
    raise SystemExit(
        "Institute name not found."
    )


# ============================================================
# GPA STATISTICS
# ============================================================

total_students = 1

gpa_5_count = 0

if gpa is not None:

    if float(gpa) == 5.0:
        gpa_5_count = 1


average_gpa = (
    float(gpa)
    if gpa is not None
    else 0
)


gpa_5_percentage = (
    (gpa_5_count / total_students) * 100
    if total_students
    else 0
)


# ============================================================
# SUBJECT STATISTICS
# ============================================================

grade_counter = Counter()

subject_statistics = []


for subject in subjects:

    code = subject.get(
        "code",
        ""
    )

    name = subject.get(
        "subject",
        ""
    )

    mark = subject.get(
        "mark"
    )

    grade = subject.get(
        "grade",
        ""
    )

    if grade:
        grade_counter[grade] += 1

    subject_statistics.append({
        "code": code,
        "subject": name,
        "mark": mark,
        "grade": grade
    })


# ============================================================
# INSTITUTION STATISTICS
# ============================================================

institution_stats = {

    "institute": institute,

    "total_students": total_students,

    "gpa_5_count": gpa_5_count,

    "gpa_5_percentage": round(
        gpa_5_percentage,
        2
    ),

    "average_gpa": round(
        average_gpa,
        2
    ),

    "grade_distribution": dict(
        grade_counter
    ),

    "subject_statistics":
        subject_statistics
}


# ============================================================
# SAVE
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        institution_stats,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# DISPLAY
# ============================================================

print(
    "\n===== INSTITUTION STATISTICS ====="
)

print(
    json.dumps(
        institution_stats,
        ensure_ascii=False,
        indent=2
    )
)

print(
    "\nSaved:",
    OUTPUT_FILE
)

print(
    "\n===== DONE ====="
)