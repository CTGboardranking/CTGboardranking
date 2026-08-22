import csv
import json
import os
import sys


INPUT_FILE = "scraper/institution_data.csv"
OUTPUT_FILE = "scraper/institutions.json"


REQUIRED_COLUMNS = [
    "Institute",
    "Total Students",
    "GPA 5 Count",
    "Average GPA",
    "A+",
    "A",
    "A-",
    "B",
    "C",
    "D",
    "F"
]


def number(value, default=0):
    """Convert a value to int/float safely."""

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    try:
        number_value = float(value)

        if number_value.is_integer():
            return int(number_value)

        return number_value

    except ValueError:
        return default


def load_csv(filename):

    with open(
        filename,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise SystemExit(
                "CSV header not found."
            )

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing:
            raise SystemExit(
                "Missing columns: "
                + ", ".join(missing)
            )

        return list(reader)


def convert(rows):

    institutions = []

    for row_number, row in enumerate(
        rows,
        start=2
    ):

        institute = str(
            row.get(
                "Institute",
                ""
            )
        ).strip()

        if not institute:
            print(
                f"Skipping row {row_number}: "
                "Institute is empty."
            )
            continue

        total_students = number(
            row.get("Total Students")
        )

        gpa_5_count = number(
            row.get("GPA 5 Count")
        )

        average_gpa = number(
            row.get("Average GPA")
        )

        grade_distribution = {}

        for grade in [
            "A+",
            "A",
            "A-",
            "B",
            "C",
            "D",
            "F"
        ]:

            grade_distribution[grade] = number(
                row.get(grade)
            )

        institutions.append({

            "institute": institute,

            "total_students":
                int(total_students),

            "gpa_5_count":
                int(gpa_5_count),

            "average_gpa":
                float(average_gpa),

            "grade_distribution":
                grade_distribution
        })

    return institutions


def main():

    if not os.path.exists(INPUT_FILE):

        raise SystemExit(
            f"\nInput file not found:\n"
            f"{INPUT_FILE}\n\n"
            "Create the CSV file first."
        )

    print(
        f"Reading: {INPUT_FILE}"
    )

    rows = load_csv(
        INPUT_FILE
    )

    institutions = convert(
        rows
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            institutions,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\n===== CONVERSION COMPLETE ====="
    )

    print(
        "Institutions:",
        len(institutions)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print(
        "\n===== DONE ====="
    )


if __name__ == "__main__":
    main()