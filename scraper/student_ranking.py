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

    # ========================================================
    # CHECK INPUT FILE
    # ========================================================

    if not os.path.exists(INPUT_FILE):

        print(
            f"Input file not found: {INPUT_FILE}"
        )

        sys.exit(1)


    # ========================================================
    # LOAD STUDENTS
    # ========================================================

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


    # ========================================================
    # VALIDATE DATA
    # ========================================================

    if not isinstance(
        students,
        list
    ):

        print(
            "students.json must contain a list."
        )

        sys.exit(1)


    rankings = []


    # ========================================================
    # CALCULATE STUDENT RANKING
    # ========================================================

    for student in students:

        subjects = student.get(
            "subjects",
            []
        )


        # ----------------------------------------------------
        # TOTAL MARKS
        # ----------------------------------------------------

        total_marks = calculate_total_marks(
            subjects
        )


        # ----------------------------------------------------
        # GRADE SCORE
        # ----------------------------------------------------

        grade_score = calculate_grade_score(
            subjects
        )


        # ----------------------------------------------------
        # GPA
        # ----------------------------------------------------

        gpa = safe_number(
            student.get(
                "gpa",
                0
            )
        )


        # ----------------------------------------------------
        # GPA CONVERTED TO 100
        # ----------------------------------------------------

        gpa_score = (
            gpa / 5
        ) * 100


        # ----------------------------------------------------
        # FINAL STUDENT SCORE
        #
        # KEEPING ORIGINAL CALCULATION UNCHANGED
        # ----------------------------------------------------

        score = (
            gpa_score * 0.50
            +
            grade_score * 0.20
            +
            min(total_marks / 10, 100)
            * 0.30
        )


        # ====================================================
        # ADD STUDENT
        # ====================================================

        rankings.append({

            # 1
            "roll":
                student.get(
                    "roll",
                    ""
                ),

            # 2
            "name":
                student.get(
                    "name",
                    "Unknown"
                ),

            # 3
            "total_marks":
                total_marks,

            # 4
            "institute":
                student.get(
                    "institute",
                    "Unknown"
                ),

            # 5
            "district":
                student.get(
                    "district",
                    "Unknown"
                ),

            # 6
            "gpa":
                gpa,

            # 7
            "grade_score":
                grade_score,

            # 8
            "score":
                round(
                    score,
                    2
                ),

            # 9
            "subjects":
                subjects
        })


    # ========================================================
    # SORTING
    #
    # KEEPING ORIGINAL RANKING LOGIC UNCHANGED
    # ========================================================

    rankings.sort(
        key=lambda x: (
            -x["score"],
            -x["gpa"],
            -x["total_marks"],
            str(x["roll"])
        )
    )


    # ========================================================
    # ASSIGN RANKS
    # ========================================================

    for rank, student in enumerate(
        rankings,
        start=1
    ):

        student["rank"] = rank


    # ========================================================
    # REBUILD JSON ORDER
    #
    # Rank first, then:
    # Roll → Name → Total Marks → Institute
    # ========================================================

    ordered_rankings = []

    for student in rankings:

        ordered_rankings.append({

            "rank":
                student["rank"],

            "roll":
                student["roll"],

            "name":
                student["name"],

            "total_marks":
                student["total_marks"],

            "institute":
                student["institute"],

            "district":
                student["district"],

            "gpa":
                student["gpa"],

            "grade_score":
                student["grade_score"],

            "score":
                student["score"],

            "subjects":
                student["subjects"]
        })


    # ========================================================
    # SAVE JSON
    # ========================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            ordered_rankings,
            file,
            ensure_ascii=False,
            indent=2
        )


    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print(
        "\n===== STUDENT RANKING =====\n"
    )


    for student in ordered_rankings:

        print(
            f"Rank #{student['rank']} | "
            f"Roll: {student['roll']} | "
            f"{student['name']} | "
            f"Total Marks: {student['total_marks']} | "
            f"Institute: {student['institute']} | "
            f"District: {student['district']} | "
            f"GPA: {student['gpa']} | "
            f"Grade Score: {student['grade_score']} | "
            f"Score: {student['score']}"
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        f"\nTotal students: "
        f"{len(ordered_rankings)}"
    )

    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        "\n===== DONE ====="
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()