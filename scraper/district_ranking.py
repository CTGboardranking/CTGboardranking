import json
import os
import sys


INPUT_FILE = "scraper/validated_institutions.json"
OUTPUT_FILE = "scraper/district_ranking.json"


# District ranking weights
WEIGHTS = {
    "average_gpa": 40,
    "gpa5_rate": 30,
    "grade_performance": 20,
    "pass_rate": 10
}


GRADE_WEIGHTS = {
    "A+": 100,
    "A": 90,
    "A-": 80,
    "B": 70,
    "C": 60,
    "D": 50,
    "F": 0
}


def clamp(
    value,
    minimum=0,
    maximum=100
):
    return max(
        minimum,
        min(value, maximum)
    )


def calculate_average_gpa(
    total_students,
    weighted_gpa
):
    if total_students <= 0:
        return 0

    return weighted_gpa / total_students


def calculate_gpa5_rate(
    total_students,
    gpa5_count
):
    if total_students <= 0:
        return 0

    return clamp(
        (gpa5_count / total_students) * 100
    )


def calculate_pass_rate(
    total_students,
    passed_students
):
    if total_students <= 0:
        return 0

    return clamp(
        (passed_students / total_students) * 100
    )


def calculate_grade_performance(
    grade_distribution
):

    total = 0
    weighted = 0

    for grade, weight in GRADE_WEIGHTS.items():

        count = grade_distribution.get(
            grade,
            0
        )

        if not isinstance(
            count,
            (int, float)
        ):
            count = 0

        if count < 0:
            count = 0

        total += count

        weighted += (
            count * weight
        )

    if total <= 0:
        return 0

    return clamp(
        weighted / total
    )


def calculate_final_score(
    average_gpa,
    gpa5_rate,
    grade_performance,
    pass_rate
):

    gpa_score = clamp(
        (average_gpa / 5.0) * 100
    )

    score = (

        gpa_score
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

        try:
            institutions = json.load(file)

        except json.JSONDecodeError as e:

            print(
                "Invalid JSON:"
            )

            print(e)

            sys.exit(1)

    if not isinstance(
        institutions,
        list
    ):

        print(
            "Invalid input format."
        )

        sys.exit(1)

    # -----------------------------
    # Group institutions by district
    # -----------------------------

    districts = {}

    for institution in institutions:

        district = str(
            institution.get(
                "district",
                ""
            )
        ).strip()

        if not district:
            continue

        if district not in districts:

            districts[district] = {

                "district": district,

                "institutions": 0,

                "total_students": 0,

                "passed_students": 0,

                "failed_students": 0,

                "gpa_5_count": 0,

                "weighted_gpa": 0,

                "grade_distribution": {
                    grade: 0
                    for grade in GRADE_WEIGHTS
                }
            }

        data = districts[district]

        total_students = institution.get(
            "total_students",
            0
        )

        passed_students = institution.get(
            "passed_students",
            0
        )

        failed_students = institution.get(
            "failed_students",
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

        data["institutions"] += 1

        data["total_students"] += (
            total_students
        )

        data["passed_students"] += (
            passed_students
        )

        data["failed_students"] += (
            failed_students
        )

        data["gpa_5_count"] += (
            gpa5_count
        )

        # Weighted average GPA
        data["weighted_gpa"] += (
            average_gpa
            * total_students
        )

        # Combine grade distributions
        for grade in GRADE_WEIGHTS:

            value = grades.get(
                grade,
                0
            )

            if isinstance(
                value,
                (int, float)
            ):

                data[
                    "grade_distribution"
                ][grade] += value

    # -----------------------------
    # Calculate district ranking
    # -----------------------------

    rankings = []

    for district, data in districts.items():

        total_students = data[
            "total_students"
        ]

        passed_students = data[
            "passed_students"
        ]

        gpa5_count = data[
            "gpa_5_count"
        ]

        average_gpa = calculate_average_gpa(
            total_students,
            data["weighted_gpa"]
        )

        gpa5_rate = calculate_gpa5_rate(
            total_students,
            gpa5_count
        )

        pass_rate = calculate_pass_rate(
            total_students,
            passed_students
        )

        grade_performance = (
            calculate_grade_performance(
                data["grade_distribution"]
            )
        )

        score = calculate_final_score(
            average_gpa,
            gpa5_rate,
            grade_performance,
            pass_rate
        )

        rankings.append({

            "district":
                district,

            "institutions":
                data["institutions"],

            "total_students":
                total_students,

            "passed_students":
                passed_students,

            "failed_students":
                data["failed_students"],

            "pass_percentage":
                round(
                    pass_rate,
                    2
                ),

            "gpa_5_count":
                gpa5_count,

            "gpa_5_percentage":
                round(
                    gpa5_rate,
                    2
                ),

            "average_gpa":
                round(
                    average_gpa,
                    4
                ),

            "grade_performance":
                round(
                    grade_performance,
                    2
                ),

            "score":
                score
        })

    # -----------------------------
    # Sort
    # -----------------------------

    rankings.sort(
        key=lambda x: (
            -x["score"],
            -x["average_gpa"],
            -x["gpa_5_percentage"],
            -x["pass_percentage"],
            x["district"]
        )
    )

    # -----------------------------
    # Assign ranks
    # -----------------------------

    for position, item in enumerate(
        rankings,
        start=1
    ):

        item["rank"] = position

    # -----------------------------
    # Save JSON
    # -----------------------------

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

    # -----------------------------
    # Print results
    # -----------------------------

    print(
        "\n===== DISTRICT RANKING =====\n"
    )

    for item in rankings:

        print(
            f"Rank #{item['rank']} | "
            f"{item['district']} | "
            f"Score: {item['score']} | "
            f"Institutions: "
            f"{item['institutions']} | "
            f"Students: "
            f"{item['total_students']} | "
            f"Passed: "
            f"{item['passed_students']} | "
            f"Failed: "
            f"{item['failed_students']} | "
            f"Pass: "
            f"{item['pass_percentage']}% | "
            f"GPA-5: "
            f"{item['gpa_5_count']} "
            f"({item['gpa_5_percentage']}%) | "
            f"Average GPA: "
            f"{item['average_gpa']}"
        )

    print(
        f"\nTotal districts: "
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