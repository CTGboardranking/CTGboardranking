import json
import os
import sys


INPUT_FILE = "scraper/students.json"
OUTPUT_FILE = "scraper/student_ranking.json"


def safe_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_total_marks(subjects):
    total = 0

    for subject in subjects:

        mark = safe_number(
            subject.get("mark", 0)
        )

        total += mark

    return round(total, 2)


def calculate_grade_score(subjects):

    grade_points = {
        "A+": 100,
        "A": 90,
        "A-": 80,
        "B": 70,
        "C": 60,
        "D": 50,
        "F": 0
    }

    total = 0
    count = 0

    for subject in subjects:

        grade = str(
            subject.get(
                "grade",
                ""
            )
        ).strip().upper()

        if grade in grade_points:

            total += grade_points[grade]
            count += 1

    if count == 0:
        return 0

    return round(
        total / count,
        2
    )


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

        try:
            students = json.load(file)

        except json.JSONDecodeError as e:

            print("Invalid JSON:")
            print(e)

            sys.exit(1)

    if not isinstance(
        students,
        list
    ):

        print(
            "students.json must contain a list."
        )

        sys.exit(1)

    rankings = []

    for student in students:

        subjects = student.get(
            "subjects",
            []
        )

        total_marks = calculate_total_marks(
            subjects
        )

        grade_score = calculate_grade_score(
            subjects
        )

        gpa = safe_number(
            student.get(
                "gpa",
                0
            )
        )

        # GPA converted to 100
        gpa_score = (
            gpa / 5
        ) * 100

        # Final student score
        score = (
            gpa_score * 0.50
            +
            grade_score * 0.20
            +
            min(total_marks / 10, 100)
            * 0.30
        )

        rankings.append({

            "roll":
                student.get(
                    "roll",
                    ""
                ),

            "name":
                student.get(
                    "name",
                    "Unknown"
                ),

            "institute":
                student.get(
                    "institute",
                    "Unknown"
                ),

            "district":
                student.get(
                    "district",
                    "Unknown"
                ),

            "gpa":
                gpa,

            "total_marks":
                total_marks,

            "grade_score":
                grade_score,

            "score":
                round(
                    score,
                    2
                ),

            "subjects":
                subjects
        })

    # Highest score first
    rankings.sort(
        key=lambda x: (
            -x["score"],
            -x["gpa"],
            -x["total_marks"],
            str(x["roll"])
        )
    )

    # Assign ranks
    for rank, student in enumerate(
        rankings,
        start=1
    ):

        student["rank"] = rank

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            rankings,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\n===== STUDENT RANKING =====\n"
    )

    for student in rankings:

        print(
            f"Rank #{student['rank']} | "
            f"Roll: {student['roll']} | "
            f"{student['name']} | "
            f"GPA: {student['gpa']} | "
            f"Total Marks: {student['total_marks']} | "
            f"Score: {student['score']}"
        )

    print(
        f"\nTotal students: "
        f"{len(rankings)}"
    )

    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        "\n===== DONE ====="
    )


if __name__ == "__main__":
    main()