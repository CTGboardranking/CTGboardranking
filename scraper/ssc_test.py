import os
import json
import time
import random
import re

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

try:
    from supabase import create_client
except ImportError:
    create_client = None


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

ATTEMPTED_FILE = os.path.join(
    OUTPUT_DIR,
    "attempted_rolls.json"
)

SUPABASE_TABLE = os.getenv(
    "SUPABASE_TABLE",
    "students"
)

YEAR = 2026
BOARD = "Chattogram Board"

BATCH_SIZE = 10000
SAVE_EVERY = 500

MIN_DELAY = 0.1
MAX_DELAY = 0.2

REQUEST_TIMEOUT = (5, 15)


# ============================================================
# ROLL RANGES
# ============================================================

ROLL_RANGES = {

    "Science": (
        100001,
        132961
    ),

    "Science Irregular": (
        700001,
        723917
    ),

    "Humanities": (
        300001,
        331193
    ),

    "Business Studies": (
        500001,
        541800
    ),
}


# ============================================================
# DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 "
        "Mobile Safari/537.36"
    ),
    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


# ============================================================
# SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# JSON HELPERS
# ============================================================

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
    ) as f:

        json.dump(
            data,
            f,
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
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"Could not load {filename}: {e}",
            flush=True
        )

        return default


def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
SUPABASE_ENABLED = False


if (
    SUPABASE_URL
    and SUPABASE_KEY
    and create_client is not None
):

    try:

        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

        SUPABASE_ENABLED = True

        print(
            "Supabase: CONNECTED",
            flush=True
        )

        print(
            "Supabase table:",
            SUPABASE_TABLE,
            flush=True
        )

    except Exception as e:

        print(
            "Supabase connection error:",
            e,
            flush=True
        )

else:

    print(
        "ERROR: Supabase is NOT configured.",
        flush=True
    )

    print(
        "SUPABASE_URL present:",
        bool(SUPABASE_URL),
        flush=True
    )

    print(
        "SUPABASE_KEY present:",
        bool(SUPABASE_KEY),
        flush=True
    )

    print(
        "supabase package available:",
        create_client is not None,
        flush=True
    )


if not SUPABASE_ENABLED:

    raise SystemExit(
        "Supabase is required. "
        "Configure SUPABASE_URL and SUPABASE_KEY."
    )


# ============================================================
# LOAD ALL SUPABASE ROLLS
#
# Supabase normally limits rows returned per request.
# Therefore pagination is used.
# ============================================================

def load_supabase_rolls():

    result = set()

    page_size = 1000
    offset = 0

    print(
        "Loading existing Supabase rolls...",
        flush=True
    )

    while True:

        try:

            response = (
                supabase
                .table(SUPABASE_TABLE)
                .select("roll")
                .range(
                    offset,
                    offset + page_size - 1
                )
                .execute()
            )

            rows = response.data or []

        except Exception as e:

            print(
                "Supabase roll loading error:",
                e,
                flush=True
            )

            raise SystemExit(
                "Could not load Supabase rolls."
            )

        if not rows:
            break

        for row in rows:

            if not isinstance(
                row,
                dict
            ):
                continue

            roll = str(
                row.get(
                    "roll",
                    ""
                )
            ).strip()

            if roll:
                result.add(roll)

        print(
            f"Loaded {len(result)} Supabase rolls...",
            flush=True
        )

        if len(rows) < page_size:
            break

        offset += page_size

    print(
        "Supabase existing rolls:",
        len(result),
        flush=True
    )

    return result


supabase_rolls = load_supabase_rolls()


# ============================================================
# LOAD LOCAL ATTEMPTED / FAILED
# ============================================================

attempted_rolls = load_json(
    "attempted_rolls.json",
    []
)

failed_rolls = load_json(
    "failed_rolls.json",
    []
)


attempted_set = set()

for item in attempted_rolls:

    if isinstance(item, dict):

        roll = str(
            item.get(
                "roll",
                ""
            )
        ).strip()

    else:

        roll = str(item).strip()

    if roll:
        attempted_set.add(roll)


failed_set = set()

for item in failed_rolls:

    if isinstance(item, dict):

        roll = str(
            item.get(
                "roll",
                ""
            )
        ).strip()

    else:

        roll = str(item).strip()

    if roll:
        failed_set.add(roll)


# ============================================================
# EXISTING LOCAL STUDENTS
# ============================================================

students = load_json(
    "students.json",
    []
)

if not isinstance(
    students,
    list
):

    students = []


# ============================================================
# GPA
# ============================================================

def parse_gpa(value):

    value = clean_text(value)

    if not value:
        return None

    upper = value.upper()

    patterns = [

        r"\bGPA\s*[:=]\s*([0-5](?:\.[0-9]{1,2})?)",

        r"\bGPA\s+([0-5](?:\.[0-9]{1,2})?)",

        r"\b([0-5]\.[0-9]{1,2})\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            try:

                value = float(
                    match.group(1)
                )

                if 0 <= value <= 5:
                    return value

            except Exception:
                pass

    return None


def find_page_gpa(soup):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    match = re.search(
        r"\bGPA\s*[:=]?\s*"
        r"([0-5](?:\.[0-9]{1,2})?)",
        text,
        re.I
    )

    if match:

        try:

            value = float(
                match.group(1)
            )

            if 0 <= value <= 5:
                return value

        except Exception:
            pass

    return None


# ============================================================
# DISTRICT
# ============================================================

def extract_district_from_institute(
    institute
):

    institute = clean_text(
        institute
    )

    if not institute:
        return ""

    known = {

        "CHITTAGONG": "Chattogram",
        "CHATTOGRAM": "Chattogram",
        "COX'S BAZAR": "Cox's Bazar",
        "COXS BAZAR": "Cox's Bazar",
        "COMILLA": "Cumilla",
        "CUMILLA": "Cumilla",
        "FENI": "Feni",
        "NOAKHALI": "Noakhali",
        "LAKSHMIPUR": "Lakshmipur",
        "CHANDPUR": "Chandpur",
        "BRAHMANBARIA": "Brahmanbaria",
        "RANGAMATI": "Rangamati",
        "KHAGRACHHARI": "Khagrachhari",
        "BANDARBAN": "Bandarban",

    }

    upper = institute.upper()

    for key, district in known.items():

        if key in upper:
            return district

    return ""


# ============================================================
# GRADE
# ============================================================

GRADE_PATTERN = re.compile(
    r"^(A\+|A-|A|B|C|D|F)$",
    re.I
)


def normalize_grade(value):

    value = clean_text(value)

    value = value.replace(
        "(",
        ""
    ).replace(
        ")",
        ""
    ).replace(
        " ",
        ""
    ).upper()

    if GRADE_PATTERN.fullmatch(value):
        return value

    return ""


# ============================================================
# SUBJECT
# ============================================================

def parse_subject_values(values):

    mark = None
    grade = ""

    for value in values:

        normalized = clean_text(
            value
        ).replace(
            " ",
            ""
        ).upper()

        match = re.fullmatch(
            r"(\d{1,3})\((A\+|A-|A|B|C|D|F)\)",
            normalized
        )

        if match:

            number = int(
                match.group(1)
            )

            if 0 <= number <= 100:

                return (
                    number,
                    match.group(2)
                )


        match = re.fullmatch(
            r"(\d{1,3})(A\+|A-|A|B|C|D|F)",
            normalized
        )

        if match:

            number = int(
                match.group(1)
            )

            if 0 <= number <= 100:

                return (
                    number,
                    match.group(2)
                )


        grade_only = normalize_grade(
            normalized
        )

        if grade_only:
            grade = grade_only
            continue


        if re.fullmatch(
            r"\d{1,3}",
            normalized
        ):

            number = int(
                normalized
            )

            if 0 <= number <= 100:
                mark = number

    return (
        mark,
        grade
    )


def parse_subjects(soup):

    subjects = []
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

            if len(values) < 2:
                continue

            code = values[0]

            if not re.fullmatch(
                r"\d{3,5}",
                code
            ):
                continue

            subject_name = values[1]

            if not subject_name:
                continue

            key = (
                code,
                subject_name
            )

            if key in seen:
                continue

            seen.add(key)

            mark, grade = parse_subject_values(
                values[2:]
            )

            combined = " ".join(
                values
            ).upper()

            optional = (
                "OPTIONAL" in combined
                or "4TH SUBJECT" in combined
                or "FOURTH SUBJECT" in combined
            )

            subjects.append({

                "code": code,

                "subject": subject_name,

                "mark": mark,

                "grade": grade,

                "optional": optional,

            })

    return subjects


# ============================================================
# TOTAL
# ============================================================

def calculate_total_score(subjects):

    total = 0
    found = False

    for subject in subjects:

        mark = subject.get("mark")

        if isinstance(mark, int):

            total += mark
            found = True

    if found:
        return total

    return None


# ============================================================
# RESULT
# ============================================================

def detect_result(
    soup,
    subjects
):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    ).upper()

    match = re.search(
        r"\bRESULT\s*[:\-]\s*(PASS|FAIL)\b",
        text
    )

    if match:
        return match.group(1)

    for subject in subjects:

        if str(
            subject.get(
                "grade",
                ""
            )
        ).upper() == "F":

            return "FAIL"

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

        "father_name": "",

        "mother_name": "",

        "session": "",

        "reg_no": "",

        "type": "",

        "institute": "",

        "district": "",

        "result": "",

        "date_of_birth": "",

        "gpa": None,

        "total_score": None,

        "subjects": [],

    }


    fields = [

        ("Roll No", "roll"),
        ("Name", "name"),
        ("Board", "board"),
        ("Father's Name", "father_name"),
        ("Father Name", "father_name"),
        ("Group", "group"),
        ("Mother's Name", "mother_name"),
        ("Mother Name", "mother_name"),
        ("Session", "session"),
        ("Reg. NO", "reg_no"),
        ("Reg. No", "reg_no"),
        ("Registration No", "reg_no"),
        ("Type", "type"),
        ("Institute", "institute"),
        ("DATE OF BIRTH", "date_of_birth"),
        ("Date of Birth", "date_of_birth"),

    ]


    for row in soup.find_all("tr"):

        values = [

            clean_text(
                cell.get_text(
                    " ",
                    strip=True
                )
            )

            for cell in row.find_all(
                ["th", "td"]
            )

        ]

        if not values:
            continue

        for label, key in fields:

            for index, value in enumerate(values):

                if value.lower() == label.lower():

                    if index + 1 < len(values):

                        result[key] = clean_text(
                            values[index + 1]
                        )


                elif value.lower().startswith(
                    label.lower() + ":"
                ):

                    result[key] = clean_text(
                        value.split(
                            ":",
                            1
                        )[1]
                    )


    result["gpa"] = find_page_gpa(soup)

    result["subjects"] = parse_subjects(
        soup
    )

    result["result"] = detect_result(
        soup,
        result["subjects"]
    )

    result["total_score"] = (
        calculate_total_score(
            result["subjects"]
        )
    )

    result["district"] = (
        extract_district_from_institute(
            result["institute"]
        )
    )


    has_data = (

        bool(result["name"])
        or
        bool(result["institute"])
        or
        len(result["subjects"]) > 0

    )

    if not has_data:
        return None


    for key in [

        "roll",
        "name",
        "board",
        "group",
        "father_name",
        "mother_name",
        "session",
        "reg_no",
        "type",
        "institute",
        "district",
        "result",
        "date_of_birth",

    ]:

        result[key] = clean_text(
            result[key]
        )


    return result


# ============================================================
# SUPABASE UPSERT
# ============================================================

def supabase_upsert_student(student):

    payload = {

        "roll": str(
            student.get(
                "roll",
                ""
            )
        ),

        "name": student.get(
            "name",
            ""
        ),

        "board": student.get(
            "board",
            ""
        ),

        "group": student.get(
            "group",
            ""
        ),

        "father_name": student.get(
            "father_name",
            ""
        ),

        "mother_name": student.get(
            "mother_name",
            ""
        ),

        "session": student.get(
            "session",
            ""
        ),

        "reg_no": student.get(
            "reg_no",
            ""
        ),

        "type": student.get(
            "type",
            ""
        ),

        "institute": student.get(
            "institute",
            ""
        ),

        "district": student.get(
            "district",
            ""
        ),

        "result": student.get(
            "result",
            ""
        ),

        "date_of_birth": student.get(
            "date_of_birth",
            ""
        ),

        "gpa": student.get(
            "gpa"
        ),

        "total_score": student.get(
            "total_score"
        ),

        "subjects": student.get(
            "subjects",
            []
        ),

    }


    response = (
        supabase
        .table(SUPABASE_TABLE)
        .upsert(
            payload,
            on_conflict="roll"
        )
        .execute()
    )

    return response


# ============================================================
# GENERATE ROLLS
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
# TARGET
# ============================================================

total_target = sum(

    end - start + 1

    for start, end
    in ROLL_RANGES.values()

)


# ============================================================
# OPEN FORM
# ============================================================

print(
    "=" * 70,
    flush=True
)

print(
    "SSC 2026 COLLECTOR",
    flush=True
)

print(
    "Supabase master database: ENABLED",
    flush=True
)

print(
    "Existing Supabase rolls:",
    len(supabase_rolls),
    flush=True
)

print(
    "Local attempted rolls:",
    len(attempted_set),
    flush=True
)

print(
    "Local failed rolls:",
    len(failed_set),
    flush=True
)

print(
    "Total target:",
    total_target,
    flush=True
)

print(
    "=" * 70,
    flush=True
)


try:

    page = session.get(

        INDIVIDUAL_URL,

        headers={
            "Referer": BASE_URL
        },

        timeout=REQUEST_TIMEOUT,

        allow_redirects=True,

    )

    page.raise_for_status()

except Exception as e:

    raise SystemExit(
        f"Could not open result page: {e}"
    )


soup = BeautifulSoup(
    page.text,
    "html.parser"
)

form = soup.find("form")

if not form:

    raise SystemExit(
        "Result form not found."
    )


form_action = clean_text(
    form.get(
        "action",
        ""
    )
)

FORM_ACTION_URL = urljoin(
    page.url,
    form_action
)

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


for select in form.find_all("select"):

    name = select.get("name")

    if not name:
        continue

    selected = select.find(
        "option",
        selected=True
    )

    if not selected:
        selected = select.find("option")

    if selected:

        base_form_data[name] = selected.get(
            "value",
            selected.get_text(
                strip=True
            )
        )


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


# ============================================================
# COUNTERS
# ============================================================

processed = 0
successful = 0
not_found = 0
errors = 0
supabase_saved = 0
supabase_errors = 0

skipped_supabase = 0
skipped_attempted = 0
skipped_failed = 0


# ============================================================
# COLLECTION
# ============================================================

for group_name, roll_number in generate_rolls():

    if processed >= BATCH_SIZE:
        break

    roll = str(roll_number)


    # --------------------------------------------------------
    # SUPABASE MASTER CHECK
    # --------------------------------------------------------

    if roll in supabase_rolls:

        skipped_supabase += 1

        continue


    # --------------------------------------------------------
    # ATTEMPTED
    # --------------------------------------------------------

    if roll in attempted_set:

        skipped_attempted += 1

        continue


    # --------------------------------------------------------
    # FAILED
    # --------------------------------------------------------

    if roll in failed_set:

        skipped_failed += 1

        continue


    processed += 1

    print(
        f"[{processed}/{BATCH_SIZE}] "
        f"{group_name} | Roll {roll}",
        flush=True
    )


    # --------------------------------------------------------
    # PERSIST ATTEMPTED
    # --------------------------------------------------------

    attempted_set.add(roll)

    attempted_rolls.append(roll)

    save_json(
        "attempted_rolls.json",
        attempted_rolls
    )


    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    form_data = dict(
        base_form_data
    )

    form_data["roll"] = roll

    for key, value in submit_fields.items():

        form_data[key] = value


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

            allow_redirects=True,

        )

    except requests.exceptions.RequestException as e:

        print(
            "REQUEST ERROR:",
            roll,
            e,
            flush=True
        )

        errors += 1

        continue


    if response.status_code >= 400:

        print(
            "HTTP ERROR:",
            roll,
            response.status_code,
            flush=True
        )

        errors += 1

        continue


    # --------------------------------------------------------
    # PARSE
    # --------------------------------------------------------

    try:

        parsed = parse_result(
            response.text,
            roll,
            group_name
        )

    except Exception as e:

        print(
            "PARSING ERROR:",
            roll,
            e,
            flush=True
        )

        errors += 1

        continue


    # --------------------------------------------------------
    # NOT FOUND
    # --------------------------------------------------------

    if parsed is None:

        not_found += 1

        failed_rolls.append({

            "roll": roll,

            "group": group_name,

            "reason": "No valid result",

        })

        failed_set.add(roll)

        save_json(
            "failed_rolls.json",
            failed_rolls
        )

        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )

        continue


    # --------------------------------------------------------
    # SUPABASE SAVE
    # --------------------------------------------------------

    try:

        supabase_upsert_student(
            parsed
        )

        supabase_saved += 1

        supabase_rolls.add(roll)

        successful += 1

        print(
            "SAVED:",
            roll,
            parsed.get("name", ""),
            flush=True
        )

    except Exception as e:

        supabase_errors += 1

        print(
            "SUPABASE ERROR:",
            roll,
            e,
            flush=True
        )


    # --------------------------------------------------------
    # LOCAL TEMPORARY SAVE
    # --------------------------------------------------------

    if successful % SAVE_EVERY == 0:

        # Only keep a temporary working copy.
        save_json(
            "students.json",
            students
        )

        save_json(
            "attempted_rolls.json",
            attempted_rolls
        )

        save_json(
            "failed_rolls.json",
            failed_rolls
        )


    time.sleep(
        random.uniform(
            MIN_DELAY,
            MAX_DELAY
        )
    )


# ============================================================
# FINAL LOCAL CHECKPOINT
# ============================================================

save_json(
    "attempted_rolls.json",
    attempted_rolls
)

save_json(
    "failed_rolls.json",
    failed_rolls
)


# ============================================================
# SUMMARY
# ============================================================

remaining = max(
    total_target - len(supabase_rolls),
    0
)

summary = {

    "year": YEAR,

    "board": BOARD,

    "target_rolls": total_target,

    "collected_total":
        len(supabase_rolls),

    "failed_total":
        len(failed_set),

    "attempted_total":
        len(attempted_set),

    "supabase_existing_total":
        len(supabase_rolls),

    "remaining":
        remaining,

    "processed_this_run":
        processed,

    "successful_this_run":
        successful,

    "not_found_this_run":
        not_found,

    "errors_this_run":
        errors,

    "supabase_saved_this_run":
        supabase_saved,

    "supabase_errors_this_run":
        supabase_errors,

    "skipped_supabase":
        skipped_supabase,

    "skipped_attempted":
        skipped_attempted,

    "skipped_failed":
        skipped_failed,

    "batch_size":
        BATCH_SIZE,

    "save_every":
        SAVE_EVERY,

    "min_delay":
        MIN_DELAY,

    "max_delay":
        MAX_DELAY,

    "roll_ranges":
        ROLL_RANGES,

}


save_json(
    "student_collection_summary.json",
    summary
)


# ============================================================
# FINAL
# ============================================================

print("")
print("=" * 70)
print("SSC COLLECTION BATCH COMPLETE")
print("=" * 70)

print(
    "Processed this run:",
    processed
)

print(
    "Successful:",
    successful
)

print(
    "Not found:",
    not_found
)

print(
    "Errors:",
    errors
)

print(
    "Supabase saved:",
    supabase_saved
)

print(
    "Supabase errors:",
    supabase_errors
)

print(
    "Skipped Supabase:",
    skipped_supabase
)

print(
    "Skipped attempted:",
    skipped_attempted
)

print(
    "Skipped failed:",
    skipped_failed
)

print(
    "Total in Supabase:",
    len(supabase_rolls)
)

print(
    "Remaining:",
    remaining
)

print("=" * 70)
print("DONE")