import json
import os

INPUT_FILE = "hsc-collector/data/institution_results.json"
OUTPUT_FILE = "hsc-collector/data/institution_ranking.json"


def safe_number(value):
    try:
        return max(0, float(value or 0))
    except (TypeError, ValueError):
        return 0


def calculate_score(item):
    appeared = safe_number(item.get("appeared"))
    passed = safe_number(item.get("passed"))
    gpa5 = safe_number(item.get("gpa5"))

    # total_gpa-এর অর্থ যাচাই না হওয়া পর্যন্ত
    # Average GPA স্কোর ব্যবহার করা হবে না।
    total_gpa = item.get("total_gpa")

    if appeared <= 0:
        return None

    if passed > appeared or gpa5 > passed:
        raise ValueError(f"Invalid result counts for EIIN {item.get('eiin')}")

    if total_gpa is None:
        raise ValueError(
            f"Average GPA unavailable for EIIN {item.get('eiin')}"
        )

    average_gpa = safe_number(total_gpa) / appeared

    if average_gpa > 5:
        raise ValueError(
            f"Invalid total_gpa for EIIN {item.get('eiin')}"
        )

    pass_rate = passed / appeared * 100
    gpa5_rate = gpa5 / appeared * 100
    gpa_score = average_gpa / 5 * 100

    return round(
        gpa_score * 0.40
        + gpa5_rate * 0.30
        + pass_rate * 0.30,
        2
    )


def main():
    if not os.path.exists(INPUT_FILE):
        raise SystemExit("HSC institution data file not found.")

    with open(INPUT_FILE, encoding="utf-8") as f:
        institutions = json.load(f)

    if not isinstance(institutions, list):
        raise SystemExit("Invalid institution data format.")

    if not institutions:
        raise SystemExit("No institution records found.")

    if not any(
        safe_number(item.get("appeared")) > 0
        for item in institutions
    ):
        raise SystemExit(
            "No verified HSC result data. Ranking generation cancelled."
        )

    for item in institutions:
        item["score"] = calculate_score(item)

    ranked = [item for item in institutions if item["score"] is not None]

    ranked.sort(
        key=lambda x: (x["score"], safe_number(x.get("passed"))),
        reverse=True
    )

    for rank, item in enumerate(ranked, 1):
        item["rank"] = rank

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)

    print("HSC institutions ranked:", len(ranked))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
