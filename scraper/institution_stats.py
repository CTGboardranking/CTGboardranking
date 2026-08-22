import json
import os
from collections import defaultdict, Counter


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = "scraper/students.json"

OUTPUT_FILE = "scraper/institution_stats.json"

VALIDATED_OUTPUT = "scraper/validated_institutions.json"


# ============================================================
# LOAD STUDENTS
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

    students = json.load(f)


if not isinstance(
    students,
    list
):

    raise SystemExit(
        "students.json must contain a list."
    )


print(
    f"Reading {len(students)} students..."
)


# ============================================================
# GROUP STUDENTS BY INSTITUTION
# ============================================================

institutions = defaultdict(list)


for student in students:

    institute = str(
        student.get(
            "institute",
            ""
        )
    ).strip()


    if not institute:
        continue


    institutions[institute].append(
        student
    )


# ============================================================
# CALCULATE INSTITUTION STATISTICS
# ============================================================

institution_results = []


for institute, institute_students in institutions.items():

    total_students = len(
        institute_students
    )


    # ========================================================
    # GPA
    # ========================================================

    gpas = []

    gpa_5_count = 0


    for student in institute_students:

        gpa = student.get(
            "gpa"
        )


        if isinstance(
            gpa,
            (int, float)
        ):

            gpa = float(gpa)

            gpas.append(
                gpa
            )


            if gpa >= 5.0:

                gpa_5_count += 1


    if gpas:

        average_gpa = (
            sum(gpas)
            / len(gpas)
        )

    else:

        average_gpa = 0


    gpa_5_percentage = (

        (
            gpa_5_count
            / total_students
        ) * 100

        if total_students

        else 0
    )


    # ========================================================
    # GRADE DISTRIBUTION
    # ========================================================

    grade_counter = Counter()


    # ========================================================
    # SUBJECT STATISTICS
    # ========================================================

    subject_data = defaultdict(
        lambda: {
            "marks": [],
            "grades": Counter()
        }
    )


    for student in institute_students:

        subjects = student.get(
            "subjects",
            []
        )


        if not isinstance(
            subjects,
            list
        ):

            continue


        for subject in subjects:

            code = str(
                subject.get(
                    "code",
                    ""
                )
            ).strip()


            name = str(
                subject.get(
                    "subject",
                    ""
                )
            ).strip()


            mark = subject.get(
                "mark"
            )


            grade = str(
                subject.get(
                    "grade",
                    ""
                )
            ).strip()


            if grade:

                grade_counter[
                    grade
                ] += 1


            key = (
                code,
                name
            )


            if isinstance(
                mark,
                (int, float)
            ):

                subject_data[key][
                    "marks"
                ].append(
                    float(mark)
                )


            if grade:

                subject_data[key][
                    "grades"
                ][grade] += 1


    # ========================================================
    # BUILD SUBJECT STATISTICS
    # ========================================================

    subject_statistics = []


    for (
        (code, name),
        data
    ) in subject_data.items():

        marks = data["marks"]


        if marks:

            average_mark = (
                sum(marks)
                / len(marks)
            )

        else:

            average_mark = 0


        subject_statistics.append({

            "code": code,

            "subject": name,

            "students_with_marks":
                len(marks),

            "average_mark":
                round(
                    average_mark,
                    2
                ),

            "grade_distribution":
                dict(
                    data["grades"]
                )
        })


    # ========================================================
    # INSTITUTION SCORE
    # ========================================================

    if average_gpa > 0:

        institution_score = (
            average_gpa
            / 5.0
        ) * 100

    else:

        institution_score = 0


    # ========================================================
    # FINAL INSTITUTION OBJECT
    # ========================================================

    institution_results.append({

        "institute":
            institute,

        "total_students":
            total_students,

        "gpa_5_count":
            gpa_5_count,

        "gpa_5_percentage":
            round(
                gpa_5_percentage,
                2
            ),

        "average_gpa":
            round(
                average_gpa,
                4
            ),

        "institution_score":
            round(
                institution_score,
                2
            ),

        "grade_distribution":
            dict(
                grade_counter
            ),

        "subject_statistics":
            subject_statistics
    })


# ============================================================
# SORT BY INSTITUTION SCORE
# ============================================================

institution_results.sort(

    key=lambda x: (

        x.get(
            "institution_score",
            0
        ),

        x.get(
            "average_gpa",
            0
        ),

        x.get(
            "gpa_5_count",
            0
        )
    ),

    reverse=True
)


# ============================================================
# ADD RANK
# ============================================================

for rank, institution in enumerate(
    institution_results,
    start=1
):

    institution["rank"] = rank


# ============================================================
# SAVE institution_stats.json
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        institution_results,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# SAVE validated_institutions.json
# ============================================================

with open(
    VALIDATED_OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        institution_results,
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
    "Students:",
    len(students)
)

print(
    "Institutions:",
    len(institution_results)
)


print(
    "\n===== TOP INSTITUTIONS ====="
)


for institution in institution_results[:10]:

    print(

        f"Rank #{institution['rank']} | "

        f"{institution['institute']} | "

        f"Students: "
        f"{institution['total_students']} | "

        f"GPA-5: "
        f"{institution['gpa_5_count']} | "

        f"Average GPA: "
        f"{institution['average_gpa']} | "

        f"Score: "
        f"{institution['institution_score']}"
    )


print(
    "\nSaved:",
    OUTPUT_FILE
)

print(
    "Saved:",
    VALIDATED_OUTPUT
)

print(
    "\n===== DONE ====="
)