import os
import json
import time
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

TABLE_NAME = "hsc_institutions"
INPUT_FILE = "hsc-collector/data/institution_results.json"
CHECKPOINT_FILE = "hsc-collector/data/institution_upload_checkpoint.json"

BATCH_SIZE = 100
MAX_RETRIES = 5
RETRY_DELAY = 3

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("ERROR: Supabase environment variables missing.")

if not os.path.exists(INPUT_FILE):
    raise SystemExit(f"ERROR: {INPUT_FILE} not found.")

with open(INPUT_FILE, encoding="utf-8") as f:
    records = json.load(f)

if not isinstance(records, list):
    raise SystemExit("ERROR: Institution data must be a JSON list.")

if not records:
    raise SystemExit("No institution records found.")

allowed_fields = {
    "eiin", "institution_name", "district", "thana",
    "appeared", "passed", "passing_rate", "gpa5",
    "total_gpa", "year", "board"
}

for index, record in enumerate(records):
    if not isinstance(record, dict) or not record.get("eiin"):
        raise SystemExit(f"Invalid EIIN at index {index}")

    if not any(
        record.get(field) not in (None, 0, 0.0, "")
        for field in ("appeared", "passed", "gpa5", "total_gpa")
    ):
        raise SystemExit(
            "No verified result data found. Upload cancelled."
        )

if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, encoding="utf-8") as f:
        checkpoint = json.load(f)
else:
    checkpoint = {"uploaded": 0, "last_index": 0, "total": len(records)}

start = min(max(int(checkpoint.get("last_index", 0)), 0), len(records))
uploaded = int(checkpoint.get("uploaded", 0))

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal"
}

url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"

print("HSC INSTITUTION UPLOADER")
print("Records:", len(records))
print("Starting index:", start)

for position in range(start, len(records), BATCH_SIZE):
    batch = records[position:position + BATCH_SIZE]
    payload = [
        {key: value for key, value in item.items() if key in allowed_fields}
        for item in batch
    ]

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                url,
                headers=headers,
                params={"on_conflict": "eiin"},
                json=payload,
                timeout=60
            )

            if response.status_code not in (200, 201, 204):
                raise RuntimeError(
                    f"Supabase error {response.status_code}: "
                    f"{response.text[:500]}"
                )

            uploaded += len(payload)
            checkpoint = {
                "uploaded": uploaded,
                "last_index": position + len(batch),
                "total": len(records)
            }

            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2)

            print("Uploaded:", uploaded)
            break

        except Exception as error:
            print("Attempt", attempt + 1, "failed:", error)

            if attempt == MAX_RETRIES - 1:
                raise SystemExit("HSC upload stopped.")

            time.sleep(RETRY_DELAY)

print("HSC INSTITUTION UPLOAD COMPLETED")
