import os
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"
INDIVIDUAL_URL = BASE_URL + "individual/"

OUTPUT_DIR = "scraper"

STUDENTS_FILE = os.path.join(
    OUTPUT_DIR,
    "students.json"
)

SUMMARY_FILE = os.path.join(
    OUTPUT_DIR,
    "student_collection_summary.json"
)

FAILED_FILE = os.path.join(
    OUTPUT_DIR,
    "failed_rolls.json"
)

# ============================================================
# SSC 2026 ROLL RANGES
# ============================================================

ROLL_RANGES = {
    "Science": (100001, 132961),
    "Science Irregular": (700001, 723917),
    "Humanities": (300001, 331193),
    "Business Studies": (500001, 541800),
}

# ============================================================
# BATCH SETTINGS
# ============================================================

BATCH_SIZE = 5000

# Faster but still keeps a small delay between requests
MIN_DELAY = 0.2
MAX_DELAY = 0.5

MAX_RETRIES = 3

REQUEST_TIMEOUT = 30


# ============================================================
# COLLECTION INFO
# ============================================================

YEAR = 2026
BOARD = "Chattogram Board"

# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),

    "Accept-Language": "en-US,en;q=0.9",

    "Connection": "keep-alive",
}


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


def save_json(filename, data):

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    temp_path = path + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_path,
        path
    )


def load_json(filename, default):

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    if not os.path.exists(path):
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return default


# ============================================================
# GPA PARSER
# ============================================================

def parse_gpa(value):

    value = clean_text(value)

    if not value:
        return None

    upper = value.upper()

    if "GPA=" in upper:

        value = upper.split(
            "GPA=",
            1
        )[1].strip()

    elif "GPA =" in upper:

        value = upper.split(
            "GPA =",
            1
        )[1].strip()

    try:

        return float(value)

    except ValueError:

        return None


# ============================================================
# SUBJECT RESULT PARSER
# ============================================================

def parse_subject_result(value):

    value = clean_text(value)

    mark = None
    grade = ""

    if "(" in value:

        mark_text = (
            value
            .split("(", 1)[0]
            .strip()
        )

        grade_text = (
            value
            .split("(", 1)[1]
            .replace(")", "")
            .strip()
        )

        try:

            mark = int(mark_text)

        except ValueError:

            mark = None

        grade = grade_text

    else:

        try:

            mark = int(value)

        except ValueError:

            mark = None

    return mark, grade


# ============================================================
# FIND VALUE AFTER LABEL
# ============================================================

def find_value_after_label(
    values,
    label
):

    label = label.lower().strip()

    for i, value in enumerate(values):

        if clean_text(value).lower() == label:

            if i + 1 < len(values):

                return clean_text(
                    values[i + 1]
                )

    return ""


# ============================================================
# PARSE RESULT
# ============================================================

def parse_result(
    html,
    requested_roll,
    group_name
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    result = {

        "roll": str(requested_roll),

        "name": "",

        "board": "",

        "group": group_name,

        "session": "",

        "type": "",

        "institute": "",

        "district": "",

        "gpa": None,

        "subjects": []
    }


    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    for row in soup.find_all("tr"):

        cells = row.find_all(
            ["th", "td"]
        )

        values = [
            clean_text(
                cell.get_text(
                    " ",
                    strip=True
                )
            )
            for cell in cells
        ]

        if not values:
            continue


        fields = [
            ("Roll No", "roll"),
            ("Name", "name"),
            ("Board", "board"),
            ("Group", "group"),
            ("Session", "session"),
            ("Type", "type"),
            ("Institute", "institute"),
            ("District", "district"),
        ]


        for label, key in fields:

            value = find_value_after_label(
                values,
                label
            )

            if value:

                result[key] = value


        result_value = find_value_after_label(
            values,
            "Result"
        )

        if result_value:

            gpa = parse_gpa(
                result_value
            )

            if gpa is not None:

                result["gpa"] = gpa


    # ========================================================
    # GPA FALLBACK
    # ========================================================

    if result["gpa"] is None:

        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

        upper = page_text.upper()

        if "GPA=" in upper:

            try:

                value = (
                    upper
                    .split("GPA=", 1)[1]
                    .split(" ", 1)[0]
                    .strip()
                )

                result["gpa"] = float(
                    value
                )

            except Exception:

                pass


    # ========================================================
    # SUBJECTS
    # ========================================================

    seen = set()

    for table in soup.find_all("table"):

        for row in table.find_all("tr"):

            cells = row.find_all(
                ["th", "td"]
            )

            values = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )
                for cell in cells
            ]

            if len(values) < 3:
                continue

            code = values[0]

            if not code.isdigit():
                continue

            subject = values[1]

            mark, grade = parse_subject_result(
                values[2]
            )

            key = (
                code,
                subject
            )

            if key in seen:
                continue

            seen.add(key)

            result["subjects"].append({

                "code": code,

                "subject": subject,

                "mark": mark,

                "grade": grade
            })


    # ========================================================
    # CLEAN VALUES
    # ========================================================

    for key in [
        "roll",
        "name",
        "board",
        "group",
        "session",
        "type",
        "institute",
        "district"
    ]:

        result[key] = clean_text(
            result[key]
        )


    return result


# ============================================================
# GENERATE ALL ROLLS
# ============================================================

def generate_rolls():

    for group_name, (
        start,
        end
    ) in ROLL_RANGES.items():

        for roll in range(
            start,
            end + 1
        ):

            yield (
                group_name,
                roll
            )


# ============================================================
# LOAD EXISTING DATA
# ============================================================

students = load_json(
    "students.json",
    []
)

failed_rolls = load_json(
    "failed_rolls.json",
    []
)


if not isinstance(
    students,
    list
):

    students = []


if not isinstance(
    failed_rolls,
    list
):

    failed_rolls = []


# ============================================================
# EXISTING SUCCESSFUL ROLLS
# ============================================================

existing_rolls = set()

for student in students:

    roll = str(
        student.get(
            "roll",
            ""
        )
    ).strip()

    if roll:

        existing_rolls.add(
            roll
        )


# ============================================================
# OPEN RESULT PAGE
# ============================================================

print(
    "Opening SSC Individual Result page..."
)

try:

    page = session.get(

        INDIVIDUAL_URL,

        headers={
            "Referer": BASE_URL
        },

        timeout=REQUEST_TIMEOUT,

        allow_redirects=True
    )

    page.raise_for_status()

except requests.RequestException as error:

    raise SystemExit(
        f"Could not open result page: {error}"
    )


print(
    "GET Status:",
    page.status_code
)

print(
    "GET URL:",
    page.url
)


# ============================================================
# FIND FORM
# ============================================================

soup = BeautifulSoup(
    page.text,
    "html.parser"
)

form = soup.find("form")

if not form:

    raise SystemExit(
        "ERROR: Result form not found."
    )


form_action = clean_text(
    form.get(
        "action",
        ""
    )
)

form_method = clean_text(
    form.get(
        "method",
        "post"
    )
).lower()


FORM_ACTION_URL = urljoin(
    page.url,
    form_action
)


print(
    "Form method:",
    form_method
)

print(
    "Form URL:",
    FORM_ACTION_URL
)


# ============================================================
# COLLECT FORM INPUTS
# ============================================================

base_form_data = {}


for inp in form.find_all("input"):

    name = inp.get("name")

    if not name:
        continue

    input_type = inp.get(
        "type",
        "text"
    ).lower()

    if input_type in [
        "submit",
        "button",
        "reset",
        "image"
    ]:

        continue

    if input_type in [
        "checkbox",
        "radio"
    ]:

        if not inp.has_attr("checked"):

            continue

    base_form_data[name] = inp.get(
        "value",
        ""
    )


# ============================================================
# SELECT FIELDS
# ============================================================

for select in form.find_all("select"):

    name = select.get("name")

    if not name:
        continue

    selected = select.find(
        "option",
        selected=True
    )

    if not selected:

        selected = select.find(
            "option"
        )

    if selected:

        base_form_data[name] = selected.get(
            "value",
            selected.get_text(
                strip=True
            )
        )


# ============================================================
# SUBMIT BUTTON
# ============================================================

submit_fields = {}

for element in form.find_all(
    ["input", "button"]
):

    element_type = element.get(
        "type",
        ""
    ).lower()

    name = element.get("name")

    if (
        element_type == "submit"
        and name
    ):

        submit_fields[name] = element.get(
            "value",
            element.get_text(
                strip=True
            )
        )


if not submit_fields:

    submit_fields = {
        "button2": "Submit"
    }


print(
    "Submit fields:",
    submit_fields
)


# ============================================================
# TOTAL ROLLS
# ============================================================

total_target = sum(
    end - start + 1
    for start, end in ROLL_RANGES.values()
)


# ============================================================
# COLLECTION COUNTERS
# ============================================================

processed_this_run = 0
success_this_run = 0
not_found_this_run = 0
error_this_run = 0


print(
    "\n========================================"
)

print(
    "SSC 2026 DATA COLLECTION"
)

print(
    "========================================"
)

print(
    "Total target rolls:",
    total_target
)

print(
    "Already collected:",
    len(existing_rolls)
)

print(
    "Remaining:",
    max(
        total_target - len(existing_rolls),
        0
    )
)

print(
    "Batch size:",
    BATCH_SIZE
)

print(
    "========================================"
)


# ============================================================
# MAIN COLLECTION LOOP
# ============================================================

for group_name, roll_number in generate_rolls():

    roll = str(
        roll_number
    )


    # --------------------------------------------------------
    # Already collected
    # --------------------------------------------------------

    if roll in existing_rolls:

        continue


    # --------------------------------------------------------
    # Batch limit
    # --------------------------------------------------------

    if processed_this_run >= BATCH_SIZE:

        break


    processed_this_run += 1


    print(
        f"\n[{processed_this_run}/{BATCH_SIZE}] "
        f"{group_name} | Roll: {roll}"
    )


    # ========================================================
    # FORM DATA
    # ========================================================

    form_data = dict(
        base_form_data
    )

    form_data["roll"] = roll


    for key, value in submit_fields.items():

        form_data[key] = value


    # ========================================================
    # REQUEST
    # ========================================================

    response = None

    last_error = None


    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.post(

                FORM_ACTION_URL,

                data=form_data,

                headers={
                    "Referer": page.url,
                    "Origin":
                        "https://sresult.bise-ctg.gov.bd",
                    "Content-Type":
                        "application/x-www-form-urlencoded",
                },

                timeout=REQUEST_TIMEOUT,

                allow_redirects=True
            )

            break

        except requests.RequestException as error:

            last_error = error

            print(
                f"Request error "
                f"(attempt {attempt}/{MAX_RETRIES}):",
                error
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    attempt * 2
                )


    # ========================================================
    # REQUEST FAILED
    # ========================================================

    if response is None:

        print(
            "REQUEST FAILED:",
            roll
        )

        error_this_run += 1

        continue


    print(
        "HTTP:",
        response.status_code
    )


    # ========================================================
    # SERVER ERROR
    # ========================================================

    if response.status_code >= 500:

        print(
            "Server error — will retry on next run."
        )

        error_this_run += 1

        continue


    # ========================================================
    # CLIENT ERROR
    # ========================================================

    if response.status_code >= 400:

        print(
            "HTTP error:",
            response.status_code
        )

        error_this_run += 1

        continue


    # ========================================================
    # PARSE
    # ========================================================

    parsed = parse_result(
        response.text,
        roll,
        group_name
    )


    # ========================================================
    # RESULT NOT FOUND
    # ========================================================

    if not parsed.get("institute"):

        print(
            "No result found."
        )

        # IMPORTANT:
        # Don't permanently mark this roll as failed.
        # It will be checked again in a future run.

        not_found_this_run += 1

        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )

        continue


    # ========================================================
    # SUCCESS
    # ========================================================

    print(
        "FOUND:",
        parsed.get("name", "")
    )

    print(
        "Institute:",
        parsed.get("institute", "")
    )

    print(
        "District:",
        parsed.get("district", "")
    )

    print(
        "GPA:",
        parsed.get("gpa")
    )

    print(
        "Subjects:",
        len(
            parsed.get(
                "subjects",
                []
            )
        )
    )


    # ========================================================
    # DUPLICATE PROTECTION
    # ========================================================

    if roll not in existing_rolls:

        students.append(
            parsed
        )

        existing_rolls.add(
            roll
        )

        success_this_run += 1


    # ========================================================
    # SAVE IMMEDIATELY
    # ========================================================

    save_json(
        "students.json",
        students
    )


    # ========================================================
    # DELAY
    # ========================================================

    time.sleep(
        random.uniform(
            MIN_DELAY,
            MAX_DELAY
        )
    )


# ============================================================
# CALCULATE REMAINING
# ============================================================

remaining = max(
    total_target - len(existing_rolls),
    0
)


# ============================================================
# SAVE SUMMARY
# ============================================================

summary = {

    "year": YEAR,

    "board": BOARD,

    "target_rolls":
        total_target,

    "collected_total":
        len(students),

    "remaining":
        remaining,

    "processed_this_run":
        processed_this_run,

    "successful_this_run":
        success_this_run,

    "not_found_this_run":
        not_found_this_run,

    "errors_this_run":
        error_this_run,

    "batch_size":
        BATCH_SIZE,

    "roll_ranges":
        ROLL_RANGES
}


save_json(
    "student_collection_summary.json",
    summary
)


# ============================================================
# FINAL OUTPUT
# ============================================================

print(
    "\n========================================"
)

print(
    "===== SSC COLLECTION BATCH COMPLETE ====="
)

print(
    "========================================"
)

print(
    "Processed:",
    processed_this_run
)

print(
    "Successful:",
    success_this_run
)

print(
    "Not found:",
    not_found_this_run
)

print(
    "Errors:",
    error_this_run
)

print(
    "Total students saved:",
    len(students)
)

print(
    "Remaining:",
    remaining
)

print(
    "Saved:",
    STUDENTS_FILE
)

print(
    "Saved:",
    SUMMARY_FILE
)

print(
    "========================================"
)

print(
    "===== DONE ====="
)


# ============================================================
# IMPORTANT
# ============================================================

if processed_this_run == 0:

    if remaining == 0:

        print(
            "\nALL AVAILABLE ROLLS HAVE BEEN PROCESSED."
        )

    else:

        print(
            "\nNo new rolls processed."
        )
