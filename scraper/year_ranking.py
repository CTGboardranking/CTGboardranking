import json
import os
import sys


INPUT_FILE = "scraper/students.json"
OUTPUT_FILE = "scraper/year_ranking.json"

# Current SSC year
CURRENT_YEAR = 2026


def calculate_student_score(student):
    """
    Calculate normalized student score.

    GPA contributes 40%
    Total marks contributes 60%
    """

    gpa = student.get("gpa")

    if not isinstance(gpa, (int, float)):
        gpa = 0

    gpa_score = (gpa / 5.0) * 100

    subjects = student.get("subjects", [])

    marks = []

    for subject in subjects:

        mark = subject.get("mark")

        if isinstance(mark, (int, float)):
            marks.append(mark)

    if marks:
        total_marks = sum(marks)

        # SSC subjects are normalized to 1200
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

    return round(score, 2), total_marks


def main():

    if not os.path.exists(INPUT_FILE):

        print(
            f"Input file not found: {INPUT_FILE}"
        )

        sys.exit(1)

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        students = json.load(file)

    if not isinstance(students, list):

        print(
            "students.json must contain a list."
        )

        sys.exit(1)

    print(
        f"Reading {len(students)} students..."
    )

    ranking = []

    for student in students:

        score, total_marks = calculate_student_score(
            student
        )

        ranking.append({

            "year": CURRENT_YEAR,

            "roll": student.get(
                "roll",
                ""
            ),

            "name": student.get(
                "name",
                ""
            ),

            "institute": student.get(
                "institute",
                ""
            ),

            "district": student.get(
                "district",
                ""
            ),

            "gpa": student.get(
                "gpa"
            ),

            "total_marks": total_marks,

            "score": score
        })


    # Highest score first
    ranking.sort(
        key=lambda x: (
            -x["score"],
            -(x["gpa"] or 0),
            -x["total_marks"],
            x["roll"]
        )
    )


    # Assign rank
    for position, student in enumerate(
        ranking,
        start=1
    ):

        student["rank"] = position


    # Save
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            ranking,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        "\n===== YEAR-WISE RANKING =====\n"
    )

    print(
        f"Year: SSC {CURRENT_YEAR}"
    )

    for student in ranking:

        print(
            f"Rank #{student['rank']} | "
            f"Roll: {student['roll']} | "
            f"{student['name']} | "
            f"GPA: {student['gpa']} | "
            f"Marks: {student['total_marks']} | "
            f"Score: {student['score']}"
        )


    print(
        f"\nTotal students: {len(ranking)}"
    )

    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        "\n===== DONE ====="
    )


if __name__ == "__main__":
    main()