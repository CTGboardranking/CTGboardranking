import json
import os
import sys


INPUT_FILE = "scraper/institutions.json"
OUTPUT_FILE = "scraper/validated_institutions.json"


GRADES = [
    "A+",
    "A",
    "A-",
    "B",
    "C",
    "D",
    "F"
]


def error(message):
    print(f"ERROR: {message}")


def validate_institution(item, index):
    errors = []

    name = item.get("institute")

    if not isinstance(name, str) or not name.strip():
        errors.append("Institute name is missing")

    total_students = item.get("total_students")

    if not isinstance(total_students, int):
        errors.append("total_students must be an integer")
    elif total_students <= 0:
        errors.append("total_students must be greater than 0")

    gpa5 = item.get("gpa_5_count")

    if not isinstance(gpa5, int):
        errors.append("gpa_5_count must be an integer")
    elif gpa5 < 0:
        errors.append("gpa_5_count cannot be negative")

    if (
        isinstance(total_students, int)
        and isinstance(gpa5, int)
        and gpa5 > total_students
    ):
        errors.append(
            "gpa_5_count cannot exceed total_students"
        )

    average_gpa = item.get("average_gpa")

    if not isinstance(
        average_gpa,
        (int, float)
    ):
        errors.append(
            "average_gpa must be a number"
        )
    elif not 0 <= average_gpa <= 5:
        errors.append(
            "average_gpa must be between 0 and 5"
        )

    grade_distribution = item.get(
        "grade_distribution"
    )

    if not isinstance(
        grade_distribution,
        dict
    ):
        errors.append(
            "grade_distribution must be an object"
        )
    else:

        for grade in GRADES:

            value = grade_distribution.get(
                grade,
                0
            )

            if not isinstance(value, int):
                errors.append(
                    f"{grade} grade count must be an integer"
                )

            elif value < 0:
                errors.append(
                    f"{grade} grade count cannot be negative"
                )

    return errors


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

        data = json.load(file)

    if not isinstance(data, list):

        print(
            "institutions.json must contain a list."
        )

        sys.exit(1)

    print(
        f"Checking {len(data)} institutions..."
    )

    valid = []
    invalid = []

    seen_names = set()

    for index, item in enumerate(
        data,
        start=1
    ):

        errors = validate_institution(
            item,
            index
        )

        name = str(
            item.get(
                "institute",
                ""
            )
        ).strip()

        normalized_name = name.lower()

        if normalized_name in seen_names:

            errors.append(
                "Duplicate institution name"
            )

        else:

            seen_names.add(
                normalized_name
            )

        if errors:

            invalid.append({
                "row": index,
                "institute": name,
                "errors": errors
            })

        else:

            valid.append(item)

    print("\n===== VALIDATION RESULT =====")

    print(
        "Total:",
        len(data)
    )

    print(
        "Valid:",
        len(valid)
    )

    print(
        "Invalid:",
        len(invalid)
    )

    if invalid:

        print(
            "\n===== INVALID RECORDS ====="
        )

        for item in invalid:

            print(
                f"\nRow {item['row']}: "
                f"{item['institute']}"
            )

            for problem in item["errors"]:

                print(
                    f"  - {problem}"
                )

        print(
            "\nValidation failed."
        )

        sys.exit(1)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            valid,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nAll records are valid."
    )

    print(
        "Saved:",
        OUTPUT_FILE
    )

    print(
        "\n===== VALIDATION PASSED ====="
    )


if __name__ == "__main__":
    main()