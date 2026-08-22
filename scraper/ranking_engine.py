import json
import os
import sys


INPUT_FILE = "scraper/validated_institutions.json"
OUTPUT_FILE = "scraper/institution_ranking.json"


# Final ranking weights
WEIGHTS = {
    "average_gpa": 40,
    "gpa5_rate": 30,
    "grade_performance": 20,
    "pass_rate": 10
}


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(value, maximum))


def calculate_gpa_score(average_gpa):
    """
    Average GPA:
    0 GPA  -> 0 score
    5 GPA  -> 100 score
    """
    return clamp(
        (average_gpa / 5.0) * 100
    )


def calculate_gpa5_rate(total_students, gpa5_count):
    """
    Percentage of students achieving GPA 5.
    """
    if total_students <= 0:
        return 0

    return clamp(
        (gpa5_count / total_students) * 100
    )


def calculate_grade_performance(grade_distribution):
    """
    Weighted subject-grade performance.

    Grade weights:
    A+ = 100
    A  = 90
    A- = 80
    B  = 70
    C  = 60
    D  = 50
    F  = 0
    """

    grade_weights = {
        "A+": 100,
        "A": 90,
        "A-": 80,
        "B": 70,
        "C": 60,
        "D": 50,
        "F": 0
    }

    total = 0
    weighted = 0

    for grade, weight in grade_weights.items():

        count = grade_distribution.get(
            grade,
            0
        )

        if not isinstance(count, (int, float)):
            count = 0

        if count < 0:
            count = 0

        total += count
        weighted += count * weight

    if total == 0:
        return 0

    return clamp(
        weighted / total
    )


def calculate_pass_rate(
    grade_distribution
):
    """
    Pass rate based on subject-grade
    distribution.

    F = failed grade.
    """

    total = sum(
        grade_distribution.get(
            grade,
            0
        )
        for grade in [
            "A+",
            "A",
            "A-",
            "B",
            "C",
            "D",
            "F"
        ]
    )

    if total == 0:
        return 0

    passed = total - grade_distribution.get(
        "F",
        0
    )

    return clamp(
        (passed / total) * 100
    )


def calculate_final_score(
    average_gpa,
    gpa5_rate,
    grade_performance,
    pass_rate
):

    score = (

        calculate_gpa_score(
            average_gpa
        )
        * WEIGHTS["average_gpa"]
        / 100

        +

        gpa5_rate
        * WEIGHTS["gpa5_rate"]
        / 100

        +

        grade_performance
        * WEIGHTS["grade_performance"]
        / 100

        +

        pass_rate
        * WEIGHTS["pass_rate"]
        / 100
    )

    return round(
        score,
        2
    )


def main():

    if not os.path.exists(
        INPUT_FILE
    ):

        print(
            f"Input file not found: "
            f"{INPUT_FILE}"
        )

        sys.exit(1)

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        institutions = json.load(
            file
        )

    if not isinstance(
        institutions,
        list
    ):

        print(
            "Invalid input format."
        )

        sys.exit(1)

    rankings = []

    for institution in institutions:

        name = institution.get(
            "institute",
            "Unknown"
        )

        total_students = institution.get(
            "total_students",
            0
        )

        gpa5_count = institution.get(
            "gpa_5_count",
            0
        )

        average_gpa = institution.get(
            "average_gpa",
            0
        )

        grades = institution.get(
            "grade_distribution",
            {}
        )

        gpa5_rate = calculate_gpa5_rate(
            total_students,
            gpa5_count
        )

        grade_performance = calculate_grade_performance(
            grades
        )

        pass_rate = calculate_pass_rate(
            grades
        )

        final_score = calculate_final_score(
            average_gpa,
            gpa5_rate,
            grade_performance,
            pass_rate
        )

        rankings.append({

            "institute": name,

            "total_students":
                total_students,

            "gpa_5_count":
                gpa5_count,

            "gpa_5_percentage":
                round(
                    gpa5_rate,
                    2
                ),

            "average_gpa":
                average_gpa,

            "grade_performance":
                round(
                    grade_performance,
                    2
                ),

            "pass_rate":
                round(
                    pass_rate,
                    2
                ),

            "score":
                final_score
        })

    # Highest score first
    rankings.sort(
        key=lambda x: (
            -x["score"],
            -x["average_gpa"],
            -x["gpa_5_percentage"],
            x["institute"]
        )
    )

    # Assign ranking positions
    for position, item in enumerate(
        rankings,
        start=1
    ):

        item["rank"] = position

    # Save JSON
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
        "\n===== INSTITUTION RANKING =====\n"
    )

    for item in rankings:

        print(
            f"Rank #{item['rank']} | "
            f"{item['institute']} | "
            f"Score: {item['score']} | "
            f"GPA-5: {item['gpa_5_count']} "
            f"({item['gpa_5_percentage']}%) | "
            f"Average GPA: "
            f"{item['average_gpa']}"
        )

    print(
        f"\nTotal institutions: "
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