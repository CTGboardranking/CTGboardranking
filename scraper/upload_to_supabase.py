import os
import json
import time
import requests


# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

TABLE_NAME = "students"

STUDENTS_FILE = "scraper/students.json"
CHECKPOINT_FILE = "scraper/supabase_upload_checkpoint.json"

BATCH_SIZE = 500

MAX_RETRIES = 5
RETRY_DELAY = 3


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

if not SUPABASE_URL:
    raise SystemExit(
        "ERROR: SUPABASE_URL secret is missing."
    )

if not SUPABASE_KEY:
    raise SystemExit(
        "ERROR: SUPABASE_KEY secret is missing."
    )


# ============================================================
# SUPABASE REST API
# ============================================================

REST_URL = (
    f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


# ============================================================
# CHECK STUDENTS FILE
# ============================================================

if not os.path.exists(STUDENTS_FILE):

    raise SystemExit(
        f"ERROR: {STUDENTS_FILE} not found."
    )


# ============================================================
# LOAD STUDENTS
# ============================================================

print("=" * 70)
print("SUPABASE SSC DATA UPLOADER")
print("=" * 70)

with open(
    STUDENTS_FILE,
    "r",
    encoding="utf-8"
) as f:

    students = json.load(f)


if not isinstance(students, list):

    raise SystemExit(
        "ERROR: students.json must contain a JSON list."
    )


TOTAL = len(students)

print("Local students:", TOTAL)


# ============================================================
# LOAD CHECKPOINT
# ============================================================

checkpoint = {
    "uploaded": 0,
    "last_index": 0,
    "total": TOTAL,
    "table": TABLE_NAME,
}


if os.path.exists(CHECKPOINT_FILE):

    try:

        with open(
            CHECKPOINT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            saved = json.load(f)

        if isinstance(saved, dict):

            checkpoint.update(saved)

    except Exception as e:

        print(
            "WARNING: Could not load checkpoint:",
            e
        )


start_index = int(
    checkpoint.get(
        "last_index",
        0
    )
)


if start_index < 0:
    start_index = 0


if start_index > TOTAL:
    start_index = TOTAL


uploaded_total = int(
    checkpoint.get(
        "uploaded",
        0
    )
)


print(
    "Checkpoint index:",
    start_index
)

print(
    "Already uploaded:",
    uploaded_total
)

print(
    "Remaining:",
    TOTAL - start_index
)

print(
    "Batch size:",
    BATCH_SIZE
)

print("=" * 70)


# ============================================================
# SAVE CHECKPOINT
# ============================================================

def save_checkpoint(
    index,
    uploaded
):

    data = {

        "uploaded": uploaded,

        "last_index": index,

        "total": TOTAL,

        "table": TABLE_NAME,

        "updated_at":
            time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
    }


    temp_file = (
        CHECKPOINT_FILE + ".tmp"
    )


    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

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


# ============================================================
# CLEAN STUDENT RECORD
# ============================================================

def clean_student(student):

    if not isinstance(
        student,
        dict
    ):

        return None


    roll = str(
        student.get(
            "roll",
            ""
        )
    ).strip()


    if not roll:

        return None


    return {

        "roll": roll,

        "name":
            student.get(
                "name",
                ""
            ),

        "board":
            student.get(
                "board",
                ""
            ),

        "group":
            student.get(
                "group",
                ""
            ),

        "session":
            student.get(
                "session",
                ""
            ),

        "type":
            student.get(
                "type",
                ""
            ),

        "institute":
            student.get(
                "institute",
                ""
            ),

        "district":
            student.get(
                "district",
                ""
            ),

        "result":
            student.get(
                "result",
                ""
            ),

        "gpa":
            student.get(
                "gpa"
            ),

        "total_score":
            student.get(
                "total_score"
            ),

        "subjects":
            student.get(
                "subjects",
                []
            ),
    }


# ============================================================
# UPLOAD ONE BATCH
# ============================================================

def upload_batch(batch):

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = requests.post(

                REST_URL,

                headers=HEADERS,

                json=batch,

                timeout=120,
            )


            if response.status_code in (
                200,
                201
            ):

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
                    f"Retryable HTTP "
                    f"{response.status_code} "
                    f"(attempt "
                    f"{attempt}/"
                    f"{MAX_RETRIES})"
                )


                if attempt < MAX_RETRIES:

                    time.sleep(
                        RETRY_DELAY * attempt
                    )

                    continue


            print(
                "Supabase upload failed."
            )

            print(
                "HTTP status:",
                response.status_code
            )

            print(
                "Response:",
                response.text[:3000]
            )

            return False


        except requests.RequestException as e:

            print(
                f"Network error "
                f"(attempt "
                f"{attempt}/"
                f"{MAX_RETRIES}):",
                e
            )


            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )

            else:

                return False


    return False


# ============================================================
# UPLOAD LOOP
# ============================================================

current_index = start_index

run_uploaded = 0

run_failed = 0


while current_index < TOTAL:


    end_index = min(

        current_index + BATCH_SIZE,

        TOTAL
    )


    raw_batch = students[
        current_index:end_index
    ]


    batch = []


    for student in raw_batch:

        record = clean_student(
            student
        )


        if record is not None:

            batch.append(
                record
            )


    print()

    print("-" * 70)

    print(
        f"Uploading records "
        f"{current_index + 1}-"
        f"{end_index}/{TOTAL}"
    )

    print(
        "Batch records:",
        len(batch)
    )


    if not batch:

        current_index = end_index

        save_checkpoint(
            current_index,
            uploaded_total
        )

        continue


    success = upload_batch(
        batch
    )


    if not success:

        run_failed += len(
            batch
        )

        print()

        print(
            "UPLOAD STOPPED."
        )

        print(
            "Checkpoint was NOT advanced."
        )

        print(
            "Run workflow again "
            "to retry this batch."
        )

        break


    uploaded_total += len(
        batch
    )


    run_uploaded += len(
        batch
    )


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


# ============================================================
# FINAL STATUS
# ============================================================

print()

print("=" * 70)

print(
    "SUPABASE UPLOAD STATUS"
)

print("=" * 70)


print(
    "Local records:",
    TOTAL
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
        TOTAL - current_index,
        0
    )
)

print(
    "Checkpoint:",
    CHECKPOINT_FILE
)

print("=" * 70)


if current_index >= TOTAL:

    print(
        "ALL LOCAL RECORDS HAVE BEEN UPLOADED."
    )

else:

    print(
        "UPLOAD IS INCOMPLETE."
    )

    print(
        "Run the workflow again "
        "to resume from checkpoint."
    )