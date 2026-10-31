import os
import json
import sys
import requests

BASE_DIR = "hsc-collector/data"
INPUT_FILE = os.path.join(
    BASE_DIR, "authorized_student_results.json"
)
INSTITUTION_FILE = os.path.join(
    BASE_DIR, "institutions.json"
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

BATCH_SIZE = 100
YEAR = 2026


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def validate_dataset(data):
    if not isinstance(data, dict):
        raise ValueError("Dataset must be a JSON object.")

    if not data.get("source"):
        raise ValueError("Dataset source is required.")

    students = data.get("students")

    if not isinstance(students, list) or not students:
        raise ValueError("No student records found.")

    seen_rolls = set()

    for index, student in enumerate(students):
        if not isinstance(student, dict):
            raise ValueError(f"Invalid student at index {index}")

        for field in ("roll", "student_name", "eiin"):
            if not student.get(field):
                raise ValueError(
                    f"Missing {field} at student index {index}"
                )

        roll = str(student["roll"]).strip()

        if roll in seen_rolls:
            raise ValueError(f"Duplicate roll: {roll}")

        seen_rolls.add(roll)

        subjects = student.get("subjects")

        if not isinstance(subjects, list) or not subjects:
            raise ValueError(
                f"No subject results for roll {roll}"
            )

        for subject in subjects:
            for field in ("subject_code", "subject_name"):
                if not subject.get(field):
                    raise ValueError(
                        f"Missing {field} for roll {roll}"
                    )

    return students


def supabase_request(table, payload, conflict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation"
    }

    response = requests.post(
        url,
        headers=headers,
        params={"on_conflict": conflict},
        json=payload,
        timeout=90
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"{table} upload failed: "
            f"{response.status_code} {response.text[:500]}"
        )

    return response.json()


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def main():
    if not os.path.exists(INPUT_FILE):
        raise SystemExit(
            f"Authorized dataset not found: {INPUT_FILE}"
        )

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SystemExit(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing."
        )

    data = load_json(INPUT_FILE)
    students = validate_dataset(data)

    institutions = load_json(INSTITUTION_FILE)
    institution_map = {
        str(item["eiin"]): item
        for item in institutions
    }

    print("Verified student records:", len(students))
    print("Dataset source:", data["source"])

    for batch in chunks(students, BATCH_SIZE):
        student_payload = []

        for item in batch:
            eiin = str(item["eiin"]).strip()
            institution = institution_map.get(eiin, {})

            student_payload.append({
                "roll": str(item["roll"]).strip(),
                "registration": item.get("registration"),
                "student_name": item["student_name"],
                "eiin": eiin,
                "institution_name": item.get(
                    "institution_name",
                    institution.get("institution_name")
                ),
                "district": item.get(
                    "district", institution.get("district")
                ),
                "thana": item.get(
                    "thana", institution.get("thana")
                ),
                "gpa": item.get("gpa"),
                "result_status": item.get("result_status"),
                "year": YEAR
            })

        saved_students = supabase_request(
            "hsc_students",
            student_payload,
            "roll,year"
        )

        student_ids = {
            str(item["roll"]): item["id"]
            for item in saved_students
        }

        subject_payload = []

        for student in batch:
            roll = str(student["roll"]).strip()
            student_id = student_ids.get(roll)

            if student_id is None:
                raise RuntimeError(
                    f"Student ID missing for roll {roll}"
                )

            for subject in student["subjects"]:
                subject_payload.append({
                    "student_id": student_id,
                    "subject_code": str(
                        subject["subject_code"]
                    ),
                    "subject_name": subject["subject_name"],
                    "marks": subject.get("marks"),
                    "letter_grade": subject.get("letter_grade"),
                    "grade_point": subject.get("grade_point"),
                    "year": YEAR
                })

        for subject_batch in chunks(
            subject_payload, BATCH_SIZE
        ):
            supabase_request(
                "hsc_subject_results",
                subject_batch,
                "student_id,subject_code,year"
            )

        print(
            "Students uploaded:",
            len(saved_students),
            "| Subject records:",
            len(subject_payload)
        )

    print("HSC STUDENT IMPORT COMPLETED")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("IMPORT ERROR:", error)
        sys.exit(1)
