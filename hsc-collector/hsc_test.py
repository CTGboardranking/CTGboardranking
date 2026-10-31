import os
import json

BASE_URL = "https://hscresult.bise-ctg.gov.bd/h22_31_x1_26/"
RESULT_URL = BASE_URL + "result.php"

INPUT_FILE = "hsc-collector/data/institutions.json"
OUTPUT_FILE = "hsc-collector/data/institution_results.json"


def normalize_institution(data):
    return {
        "eiin": str(data.get("eiin", "")).strip(),
        "institution_name": data.get("institution_name", ""),
        "district": data.get("district", ""),
        "thana": data.get("thana", ""),
        "appeared": int(data.get("appeared", 0) or 0),
        "passed": int(data.get("passed", 0) or 0),
        "passing_rate": float(data.get("passing_rate", 0) or 0),
        "gpa5": int(data.get("gpa5", 0) or 0),
        "total_gpa": data.get("total_gpa"),
        "year": 2026,
        "board": "Chattogram Board"
    }


def create_result_template():
    with open(INPUT_FILE, encoding="utf-8") as f:
        institutions = json.load(f)

    records = []

    for institution in institutions:
        records.append(normalize_institution(institution))

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print("Institution result template created:", len(records))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    print("HSC 2026 Institution Collector")
    print("Result endpoint:", RESULT_URL)
    create_result_template()
