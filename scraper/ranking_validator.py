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


def validate_institution(item, index):
    errors = []

    # -----------------------------
    # Institute
    # -----------------------------

    name = item.get("institute")

    if not isinstance(name, str) or not name.strip():
        errors.append(
            "Institute name is missing"
        )

    # -----------------------------
    # District
    # -----------------------------

    district = item.get("district")

    if not isinstance(
        district,
        str
    ) or not district.strip():

        errors.append(
            "District is missing"
        )

    # -----------------------------
    # Total Students
    # -----------------------------

    total_students = item.get(
        "total_students"
    )

    if not isinstance(
        total_students,
        int
    ):

        errors.append(
            "total_students must be an integer"
        )

    elif total_students <= 0:

        errors.append(
            "total_students must be greater than 0"
        )

    # -----------------------------
    # Passed Students
    # -----------------------------

    passed_students = item.get(
        "passed_students"
    )

    if not isinstance(
        passed_students,
        int
    ):

        errors.append(
            "passed_students must be an integer"
        )

    elif passed_students < 0:

        errors.append(
            "passed_students cannot be negative"
        )

    # -----------------------------
    # Failed Students
    # -----------------------------

    failed_students = item.get(
        "failed_students"
    )

    if not isinstance(
        failed_students,
        int
    ):

        errors.append(
            "failed_students must be an integer"
        )

    elif failed_students < 0:

        errors.append(
            "failed_students cannot be negative"
        )

    # -----------------------------
    # Passed + Failed
    # Must equal Total
    # -----------------------------

    if (
        isinstance(
            total_students,
            int
        )
        and isinstance(
            passed_students,
            int
        )
        and isinstance(
            failed_students,
            int
        )
    ):

        if (
            passed_students
            + failed_students
            != total_students
        ):

            errors.append(
                "passed_students + "
                "failed_students must equal "
                "total_students"
            )

    # -----------------------------
    # GPA 5 Count
    # -----------------------------

    gpa5 = item.get(
        "gpa_5_count"
    )

    if not isinstance(
        gpa5,
        int
    ):

        errors.append(
            "gpa_5_count must be an integer"
        )

    elif gpa5 < 0:

        errors.append(
            "gpa_5_count cannot be negative"
        )

    if (
        isinstance(
            total_students,
            int
        )
        and isinstance(
            gpa5,
            int
        )
        and gpa5 > total_students
    ):

        errors.append(
            "gpa_5_count cannot exceed "
            "total_students"
        )

    # -----------------------------
    # Average GPA
    # -----------------------------

    average_gpa = item.get(
        "average_gpa"
    )

    if not isinstance(
        average_gpa,
        (int, float)
    ):

        errors.append(
            "average_gpa must be a number"
        )

    elif not 0 <= average_gpa <= 5:

        errors.append(
            "average_gpa must be between "
            "0 and 5"
        )

    # -----------------------------
    # Grade Distribution
    # -----------------------------

    grade_distribution = item.get(
        "grade_distribution"
    )

    if not isinstance(
        grade_distribution,
        dict
    ):

        errors.append(
            "grade_distribution must be "
            "an object"
        )

    else:

        for grade in GRADES:

            value = grade_distribution.get(
                grade,
                0
            )

            if not isinstance(
                value,
                int
            ):

                errors.append(
                    f"{grade} grade count "
                    "must be an integer"
                )

            elif value < 0:

                errors.append(
                    f"{grade} grade count "
                    "cannot be negative"
                )

    return errors


def main():

    # -----------------------------
    # Check input file
    # -----------------------------

    if not os.path.exists(
        INPUT_FILE
    ):

        print(
            f"Input file not found: "
            f"{INPUT_FILE}"
        )

        sys.exit(1)

    # -----------------------------
    # Load JSON
    # -----------------------------

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        try:

            data = json.load(
                file
            )

        except json.JSONDecodeError as e:

            print(
                "Invalid JSON:"
            )

            print(e)

            sys.exit(1)

    # -----------------------------
    # Check list
    # -----------------------------

    if not isinstance(
        data,
        list
    ):

        print(
            "institutions.json must "
            "contain a list."
        )

        sys.exit(1)

    print(
        f"Checking {len(data)} institutions..."
    )

    valid = []
    invalid = []

    seen_names = set()

    # -----------------------------
    # Validate records
    # -----------------------------

    for index, item in enumerate(
        data,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            invalid.append({
                "row": index,
                "institute": "",
                "errors": [
                    "Institution record "
                    "must be an object"
                ]
            })

            continue

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

        normalized_name = (
            name.lower()
        )

        # -------------------------
        # Duplicate institution
        # -------------------------

        if normalized_name:

            if normalized_name in seen_names:

                errors.append(
                    "Duplicate institution name"
                )

            else:

                seen_names.add(
                    normalized_name
                )

        # -------------------------
        # Save result
        # -------------------------

        if errors:

            invalid.append({
                "row": index,
                "institute": name,
                "errors": errors
            })

        else:

            valid.append(
                item
            )

    # -----------------------------
    # Validation summary
    # -----------------------------

    print(
        "\n===== VALIDATION RESULT ====="
    )

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

    # -----------------------------
    # Invalid records
    # -----------------------------

    if invalid:

        print(
            "\n===== INVALID RECORDS ====="
        )

        for item in invalid:

            print(
                f"\nRow {item['row']}: "
                f"{item['institute']}"
            )

            for problem in item[
                "errors"
            ]:

                print(
                    f"  - {problem}"
                )

        print(
            "\nValidation failed."
        )

        sys.exit(1)

    # -----------------------------
    # Save validated data
    # -----------------------------

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