import json
import os
import sys


STUDENTS_FILE = "scraper/students.json"
INSTITUTIONS_FILE = "scraper/validated_institutions.json"

OUTPUT_FILE = "scraper/board_ranking.json"

BOARD_NAME = "Chattogram Board"
YEAR = 2026


def average(values):

    values = [
        value
        for value in values
        if isinstance(value, (int, float))
    ]

    if not values:
        return 0

    return sum(values) / len(values)


def calculate_student_score(student):

    gpa = student.get("gpa", 0)

    if not isinstance(gpa, (int, float)):
        gpa = 0

    gpa_score = min(
        (gpa / 5.0) * 100,
        100
    )

    subjects = student.get(
        "subjects",
        []
    )

    marks = []

    for subject in subjects:

        mark = subject.get("mark")

        if isinstance(mark, (int, float)):
            marks.append(mark)

    if marks:

        total_marks = sum(marks)

        marks_score = min(
            (total_marks / 1200) * 100,
            100
        )

    else:

        total_marks = 0
        marks_score = 0

    score = (
        gpa_score * 0.40
        +
        marks_score * 0.60
    )

    return round(score, 2)


def calculate_board_score(
    average_gpa,
    average_student_score,
    institution_score
):

    gpa_score = min(
        (average_gpa / 5.0) * 100,
        100
    )

    score = (
        gpa_score * 0.40
        +
        average_student_score * 0.40
        +
        institution_score * 0.20
    )

    return round(score, 2)


def main():

    if not os.path.exists(STUDENTS_FILE):

        print(
            f"Input file not found: {STUDENTS_FILE}"
        )

        sys.exit(1)

    if not os.path.exists(INSTITUTIONS_FILE):

        print(
            f"Input file not found: "
            f"{INSTITUTIONS_FILE}"
        )

        sys.exit(1)


    # ========================================================
    # LOAD STUDENTS
    # ========================================================

    with open(
        STUDENTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        students = json.load(file)


    if not isinstance(
        students,
        list
    ):

        print(
            "students.json must contain a list."
        )

        sys.exit(1)


    # ========================================================
    # LOAD INSTITUTIONS
    # ========================================================

    with open(
        INSTITUTIONS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        institutions = json.load(file)


    if not isinstance(
        institutions,
        list
    ):

        print(
            "validated_institutions.json "
            "must contain a list."
        )

        sys.exit(1)


    print(
        f"Reading {len(students)} students..."
    )

    print(
        f"Reading {len(institutions)} institutions..."
    )


    # ========================================================
    # STUDENT STATISTICS
    # ========================================================

    student_gpas = []

    student_scores = []

    gpa5_count = 0

    total_students = len(students)


    for student in students:

        gpa = student.get(
            "gpa"
        )

        if isinstance(
            gpa,
            (int, float)
        ):

            student_gpas.append(gpa)

            if gpa >= 5.0:

                gpa5_count += 1


        score = calculate_student_score(
            student
        )

        student_scores.append(
            score
        )


    average_gpa = round(
        average(student_gpas),
        4
    )


    average_student_score = round(
        average(student_scores),
        2
    )


    if total_students > 0:

        gpa5_percentage = round(
            (
                gpa5_count
                / total_students
            ) * 100,
            2
        )

    else:

        gpa5_percentage = 0


    # ========================================================
    # INSTITUTION STATISTICS
    # ========================================================

    institution_scores = []

    total_institution_students = 0

    total_institution_gpa5 = 0


    for institution in institutions:

        total_institution_students += (
            institution.get(
                "total_students",
                0
            )
        )

        total_institution_gpa5 += (
            institution.get(
                "gpa_5_count",
                0
            )
        )


        average_gpa_institution = (
            institution.get(
                "average_gpa",
                0
            )
        )


        if isinstance(
            average_gpa_institution,
            (int, float)
        ):

            institution_scores.append(
                (
                    average_gpa_institution
                    / 5.0
                ) * 100
            )


    average_institution_score = round(
        average(
            institution_scores
        ),
        2
    )


    # ========================================================
    # BOARD SCORE
    # ========================================================

    board_score = calculate_board_score(

        average_gpa,

        average_student_score,

        average_institution_score
    )


    # ========================================================
    # BOARD RESULT
    # ========================================================

    result = {

        "rank": 1,

        "board": BOARD_NAME,

        "year": YEAR,

        "score": board_score,

        "statistics": {

            "students_tested":
                total_students,

            "average_gpa":
                average_gpa,

            "gpa_5_count":
                gpa5_count,

            "gpa_5_percentage":
                gpa5_percentage,

            "average_student_score":
                average_student_score,

            "institutions":
                len(institutions),

            "institution_students":
                total_institution_students,

            "institution_gpa5":
                total_institution_gpa5,

            "average_institution_score":
                average_institution_score
        }
    }


    # ========================================================
    # SAVE
    # ========================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )


    # ========================================================
    # DISPLAY
    # ========================================================

    print(
        "\n===== BOARD RANKING =====\n"
    )

    print(
        f"Rank #1 | {BOARD_NAME} | "
        f"Year: {YEAR} | "
        f"Score: {board_score}"
    )

    print(
        f"Students: {total_students} | "
        f"GPA-5: {gpa5_count} "
        f"({gpa5_percentage}%) | "
        f"Average GPA: {average_gpa}"
    )

    print(
        f"Institutions: {len(institutions)}"
    )

    print(
        f"Average Student Score: "
        f"{average_student_score}"
    )

    print(
        f"Average Institution Score: "
        f"{average_institution_score}"
    )

    print(
        f"\nSaved: {OUTPUT_FILE}"
    )

    print(
        "\n===== DONE ====="
    )


if __name__ == "__main__":
    main()