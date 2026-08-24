import os
import json
import time
import requests

SUPABASE_URL = os.getenv("https://mpnjnyejpqeqguxikvnl.supabase.co", "").rstrip("/")
SUPABASE_KEY = os.getenv("sb_publishable_6Pm2-m3BeYB8VDw4kwCccg_WnYe5-IT", "")

TABLE_NAME = "students"

STUDENTS_FILE = "scraper/students.json"
CHECKPOINT_FILE = "scraper/supabase_upload_checkpoint.json"

BATCH_SIZE = 500
MAX_RETRIES = 5
RETRY_DELAY = 3

if not SUPABASE_URL:
    raise SystemExit("ERROR: SUPABASE_URL secret is missing.")

if not SUPABASE_KEY:
    raise SystemExit("ERROR: SUPABASE_KEY secret is missing.")

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}

if not os.path.exists(STUDENTS_FILE):
    raise SystemExit(f"ERROR: {STUDENTS_FILE} not found.")

print("=" * 70)
print("SUPABASE SSC DATA UPLOADER")
print("=" * 70)

with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
    students = json.load(f)

if not isinstance(students, list):
    raise SystemExit("ERROR: students.json must contain a JSON list.")

print("Local students:", len(students))

checkpoint = {
    "uploaded": 0,
    "last_index": 0,
    "total": len(students),
}

if os.path.exists(CHECKPOINT_FILE):
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)

        if isinstance(saved, dict):
            checkpoint.update(saved)

    except Exception as e:
        print("WARNING: Could not load checkpoint:", e)

start_index = int(checkpoint.get("last_index", 0))

if start_index < 0:
    start_index = 0

if start_index > len(students):
    start_index = len(students)

uploaded_total = int(
    checkpoint.get("uploaded", 0)
)

print("Checkpoint index:", start_index)
print("Already uploaded:", uploaded_total)
print("Remaining:", len(students) - start_index)
print("Batch size:", BATCH_SIZE)

print("=" * 70)


def save_checkpoint(index, uploaded):

    data = {
        "uploaded": uploaded,
        "last_index": index,
        "total": len(students),
        "table": TABLE_NAME,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    temp_file = CHECKPOINT_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        CHECKPOINT_FILE
    )


def clean_student(student):

    if not isinstance(student, dict):
        return None

    roll = str(
        student.get("roll", "")
    ).strip()

    if not roll:
        return None

    return {
        "roll": roll,
        "name": student.get("name", ""),
        "board": student.get("board", ""),
        "group": student.get("group", ""),
        "session": student.get("session", ""),
        "type": student.get("type", ""),
        "institute": student.get("institute", ""),
        "district": student.get("district", ""),
        "result": student.get("result", ""),
        "gpa": student.get("gpa"),
        "total_score": student.get("total_score"),
        "subjects": student.get("subjects", []),
    }


def upload_batch(batch):

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = requests.post(
                REST_URL,
                headers=HEADERS,
                json=batch,
                timeout=60,
            )

            if response.status_code in (200, 201):

                return True

            if response.status_code in (
                408,
                409,
                425,
                429,
                500,
                502,
                503,
                504,
            ):

                print(
                    f"Retryable HTTP {response.status_code} "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )

                time.sleep(
                    RETRY_DELAY * attempt
                )

                continue

            print(
                "Supabase upload failed."
            )

            print(
                "HTTP:",
                response.status_code
            )

            print(
                response.text[:2000]
            )

            return False

        except requests.RequestException as e:

            print(
                f"Network error "
                f"(attempt {attempt}/{MAX_RETRIES}):",
                e
            )

            time.sleep(
                RETRY_DELAY * attempt
            )

    return False


current_index = start_index
run_uploaded = 0
run_failed = 0

while current_index < len(students):

    end_index = min(
        current_index + BATCH_SIZE,
        len(students)
    )

    raw_batch = students[
        current_index:end_index
    ]

    batch = []

    for student in raw_batch:

        record = clean_student(student)

        if record is not None:
            batch.append(record)

    if not batch:

        current_index = end_index

        save_checkpoint(
            current_index,
            uploaded_total
        )

        continue

    print()
    print("-" * 70)

    print(
        f"Uploading records "
        f"{current_index + 1}-{end_index}"
        f"/{len(students)}"
    )

    print(
        "Batch records:",
        len(batch)
    )

    success = upload_batch(batch)

    if not success:

        run_failed += len(batch)

        print()
        print("UPLOAD STOPPED.")
        print(
            "Checkpoint was NOT advanced."
        )
        print(
            "Run again to retry this batch."
        )

        break

    uploaded_total += len(batch)
    run_uploaded += len(batch)

    current_index = end_index

    save_checkpoint(
        current_index,
        uploaded_total
    )

    print(
        "Batch uploaded successfully."
    )

    print(
        "Uploaded this run:",
        run_uploaded
    )

    print(
        "Total uploaded:",
        uploaded_total
    )

    print(
        "Next index:",
        current_index
    )

    time.sleep(0.5)


print()
print("=" * 70)
print("SUPABASE UPLOAD STATUS")
print("=" * 70)

print(
    "Local records:",
    len(students)
)

print(
    "Uploaded according to checkpoint:",
    uploaded_total
)

print(
    "Uploaded this run:",
    run_uploaded
)

print(
    "Failed this run:",
    run_failed
)

print(
    "Current index:",
    current_index
)

print(
    "Remaining:",
    max(
        len(students) - current_index,
        0
    )
)

print(
    "Checkpoint:",
    CHECKPOINT_FILE
)

print("=" * 70)

if current_index >= len(students):

    print(
        "ALL LOCAL RECORDS HAVE BEEN UPLOADED."
    )

else:

    print(
        "UPLOAD IS INCOMPLETE."
    )

    print(
        "Run again to resume from checkpoint."
    )
