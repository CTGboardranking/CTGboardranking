import os
import json
import time
import random
import re

import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ============================================================
# CONFIG
# ============================================================

BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/"
)

INDIVIDUAL_URL = (
    BASE_URL +
    "individual/"
)

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
# COLLECTION SETTINGS
# ============================================================

BATCH_SIZE = 1

SAVE_EVERY = 600

MIN_DELAY = 0.1

MAX_DELAY = 0.2

print(
    "========================================",
    flush=True
)

print(
    "SSC STUDENT COLLECTOR - FULL VERSION",
    flush=True
)

print(
    "MIN_DELAY:",
    MIN_DELAY,
    flush=True
)

print(
    "MAX_DELAY:",
    MAX_DELAY,
    flush=True
)

print(
    "========================================",
    flush=True
)


REQUEST_TIMEOUT = (
    5,
    15
)

YEAR = 2026

BOARD = "Chattogram Board"


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

    "Accept-Language":
        "en-US,en;q=0.9",

    "Connection":
        "keep-alive",
}


# ============================================================
# DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


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


def save_json(
    filename,
    data
):

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    temp_path = (
        path +
        ".tmp"
    )

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


def load_json(
    filename,
    default
):

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
            f"Could not load "
            f"{filename}: {e}",
            flush=True
        )

        return default


# ============================================================
# NUMBER HELPER
# ============================================================

def extract_number(value):

    value = clean_text(
        value
    )

    if not value:

        return None

    match = re.search(
        r"(?<!\d)(\d{1,3})(?:\.\d+)?(?!\d)",
        value
    )

    if not match:

        return None

    try:

        return int(
            match.group(1)
        )

    except Exception:

        return None


# ============================================================
# GPA
# ============================================================

def parse_gpa(value):

    value = clean_text(
        value
    )

    if not value:

        return None

    upper = value.upper()

    patterns = [

        r"\bGPA\s*=\s*([0-5](?:\.[0-9]{1,2})?)",

        r"\bGPA\s*:\s*([0-5](?:\.[0-9]{1,2})?)",

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


# ============================================================
# FIND GPA FROM PAGE
# ============================================================

def find_page_gpa(soup):

    # --------------------------------------------------------
    # 1. Search complete text
    # --------------------------------------------------------

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    upper = page_text.upper()

    patterns = [

        r"\bGPA\s*[:=]\s*([0-5](?:\.[0-9]{1,2})?)",

        r"\bGPA\s+([0-5](?:\.[0-9]{1,2})?)",

        r"\bRESULT\s*[:=]?\s*GPA\s*[:=]?\s*"
        r"([0-5](?:\.[0-9]{1,2})?)",

        r"\bFINAL\s+RESULT\s*[:=]?\s*"
        r"([0-5](?:\.[0-9]{1,2})?)",

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


    # --------------------------------------------------------
    # 2. Search table cells
    # --------------------------------------------------------

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

        for index, value in enumerate(values):

            upper_value = value.upper()

            if "GPA" in upper_value:

                gpa = parse_gpa(
                    value
                )

                if gpa is not None:

                    return gpa


                if index + 1 < len(values):

                    gpa = parse_gpa(
                        values[index + 1]
                    )

                    if gpa is not None:

                        return gpa

    return None


# ============================================================
# TOTAL SCORE DIRECT
# ============================================================

def parse_total_score_direct(soup):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    upper = text.upper()

    patterns = [

        r"\bTOTAL\s*SCORE\s*[:=]\s*(\d{2,4})",

        r"\bTOTAL\s*MARKS\s*[:=]\s*(\d{2,4})",

        r"\bTOTAL\s*MARK\s*[:=]\s*(\d{2,4})",

        r"\bTOTAL\s*[:=]\s*(\d{2,4})",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            try:

                return int(
                    match.group(1)
                )

            except Exception:

                pass

    return None


# ============================================================
# SUBJECT RESULT
# ============================================================

def parse_subject_result(
    values
):

    mark = None

    grade = ""

    # --------------------------------------------------------
    # Need at least subject information
    # --------------------------------------------------------

    if len(values) < 3:

        return (
            None,
            ""
        )


    # --------------------------------------------------------
    # Try cells after subject name
    # --------------------------------------------------------

    candidates = values[2:]


    # --------------------------------------------------------
    # First look for combined value:
    #
    # 75 A
    # 75 (A+)
    # 75(A)
    #
    # --------------------------------------------------------

    for value in candidates:

        value = clean_text(
            value
        )

        if not value:

            continue


        # ----------------------------------------------------
        # Mark + grade
        # ----------------------------------------------------

        match = re.match(
            r"^\s*(\d{1,3})\s*"
            r"(?:\(\s*([A-F][+]?)\s*\)"
            r"|([A-F][+]?))?\s*$",
            value,
            re.I
        )

        if match:

            try:

                number = int(
                    match.group(1)
                )

                # Marks normally 0-100
                if 0 <= number <= 100:

                    mark = number

                    grade = (
                        match.group(2)
                        or
                        match.group(3)
                        or
                        ""
                    )

                    return (
                        mark,
                        grade.upper()
                    )

            except Exception:

                pass


        # ----------------------------------------------------
        # Plain numeric cell
        # ----------------------------------------------------

        if value.isdigit():

            try:

                number = int(
                    value
                )

                if 0 <= number <= 100:

                    mark = number

                    continue

            except Exception:

                pass


    # --------------------------------------------------------
    # If mark found but grade is empty
    # --------------------------------------------------------

    if mark is not None:

        for value in candidates:

            upper = clean_text(
                value
            ).upper()

            if re.fullmatch(
                r"[A-F][+]?",
                upper
            ):

                grade = upper

                break

        return (
            mark,
            grade
        )


    return (
        None,
        ""
    )


# ============================================================
# LABEL VALUE
# ============================================================

def find_value_after_label(
    values,
    label
):

    label = (
        label
        .lower()
        .strip()
    )

    for i, value in enumerate(values):

        current = (
            clean_text(value)
            .lower()
        )

        if current == label:

            if (
                i + 1 <
                len(values)
            ):

                return clean_text(
                    values[i + 1]
                )

    return ""


# ============================================================
# DISTRICT FROM INSTITUTE
# ============================================================

def extract_district_from_institute(
    institute
):

    institute = clean_text(
        institute
    )

    if not institute:

        return ""

    known_districts = [

        "CHITTAGONG",

        "CHATTOGRAM",

        "COX'S BAZAR",

        "COXS BAZAR",

        "COMILLA",

        "CUMILLA",

        "FENI",

        "NOAKHALI",

        "LAKSHMIPUR",

        "CHANDPUR",

        "BRAHMANBARIA",

        "RANGAMATI",

        "KHAGRACHHARI",

        "BANDARBAN",

    ]

    upper = institute.upper()

    for district in known_districts:

        if district in upper:

            if district in (
                "CHITTAGONG",
                "CHATTOGRAM"
            ):

                return "Chattogram"

            if district in (
                "COX'S BAZAR",
                "COXS BAZAR"
            ):

                return "Cox's Bazar"

            if district in (
                "COMILLA",
                "CUMILLA"
            ):

                return "Cumilla"

            if district == "LAKSHMIPUR":

                return "Lakshmipur"

            return district.title()

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

        "roll":
            str(requested_roll),

        "name":
            "",

        "board":
            "",

        "group":
            group_name,

        "session":
            "",

        "type":
            "",

        "institute":
            "",

        "district":
            "",

        "gpa":
            None,

        "total_score":
            None,

        "subjects":
            [],

    }


    # ========================================================
    # TABLE DATA
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

            value = (
                find_value_after_label(
                    values,
                    label
                )
            )

            if value:

                result[key] = value


        # ----------------------------------------------------
        # RESULT / GPA
        # ----------------------------------------------------

        result_value = (
            find_value_after_label(
                values,
                "Result"
            )
        )

        if result_value:

            gpa = parse_gpa(
                result_value
            )

            if gpa is not None:

                result["gpa"] = gpa


        # ----------------------------------------------------
        # GPA direct label
        # ----------------------------------------------------

        for index, value in enumerate(values):

            if "GPA" in value.upper():

                gpa = parse_gpa(
                    value
                )

                if gpa is not None:

                    result["gpa"] = gpa

                elif index + 1 < len(values):

                    gpa = parse_gpa(
                        values[index + 1]
                    )

                    if gpa is not None:

                        result["gpa"] = gpa


    # ========================================================
    # GPA FALLBACK
    # ========================================================

    if result["gpa"] is None:

        result["gpa"] = find_page_gpa(
            soup
        )


    # ========================================================
    # DIRECT TOTAL SCORE
    # ========================================================

    result["total_score"] = (
        parse_total_score_direct(
            soup
        )
    )


    # ========================================================
    # DISTRICT FALLBACK
    # ========================================================

    if not result["district"]:

        result["district"] = (
            extract_district_from_institute(
                result["institute"]
            )
        )


    # ========================================================
    # SUBJECTS
    # ========================================================

    seen = set()

    subject_marks = []


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


            code = values[0].strip()


            # ------------------------------------------------
            # Subject code
            # ------------------------------------------------

            if not re.fullmatch(
                r"\d{3,5}",
                code
            ):

                continue


            subject = values[1]


            if not subject:

                continue


            mark, grade = (
                parse_subject_result(
                    values
                )
            )


            key = (
                code,
                subject
            )


            if key in seen:

                continue


            seen.add(
                key
            )


            # ------------------------------------------------
            # Optional / 4th subject detection
            # ------------------------------------------------

            combined_text = (
                " ".join(values)
                .upper()
            )

            is_optional = (
                "OPTIONAL" in combined_text
                or
                "4TH SUBJECT" in combined_text
                or
                "FOURTH SUBJECT" in combined_text
            )


            subject_data = {

                "code":
                    code,

                "subject":
                    subject,

                "mark":
                    mark,

                "grade":
                    grade,

                "optional":
                    is_optional,

            }


            result["subjects"].append(
                subject_data
            )


            # ------------------------------------------------
            # Total score source
            # ------------------------------------------------

            if mark is not None:

                subject_marks.append(
                    mark
                )


    # ========================================================
    # TOTAL SCORE FALLBACK
    # ========================================================

    if result["total_score"] is None:

        if subject_marks:

            result["total_score"] = sum(
                subject_marks
            )


    # ========================================================
    # DEBUG INFORMATION
    # ========================================================

    if not result["subjects"]:

        print(
            "WARNING: No subject rows detected.",
            flush=True
        )


    # ========================================================
    # CLEAN
    # ========================================================

    for key in [

        "roll",
        "name",
        "board",
        "group",
        "session",
        "type",
        "institute",
        "district",

    ]:

        result[key] = clean_text(
            result[key]
        )


    return result


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
# LOAD EXISTING
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
# EXISTING ROLLS
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
# TARGET
# ============================================================

total_target = sum(

    end - start + 1

    for start, end
    in ROLL_RANGES.values()

)


# ============================================================
# START
# ============================================================

print(
    "=" * 70,
    flush=True
)

print(
    "SSC 2026 STUDENT DATA COLLECTOR",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Target rolls:",
    total_target,
    flush=True
)

print(
    "Already collected:",
    len(existing_rolls),
    flush=True
)

print(
    "Remaining:",
    max(
        total_target -
        len(existing_rolls),
        0
    ),
    flush=True
)

print(
    "Batch size:",
    BATCH_SIZE,
    flush=True
)

print(
    "=" * 70,
    flush=True
)


# ============================================================
# OPEN RESULT PAGE
# ============================================================

print(
    "Opening SSC result page...",
    flush=True
)

try:

    page = session.get(

        INDIVIDUAL_URL,

        headers={
            "Referer":
                BASE_URL
        },

        timeout=
            REQUEST_TIMEOUT,

        allow_redirects=True,

    )

    page.raise_for_status()


except Exception as e:

    raise SystemExit(
        f"Could not open result page: {e}"
    )


print(
    "GET Status:",
    page.status_code,
    flush=True
)

print(
    "GET URL:",
    page.url,
    flush=True
)


# ============================================================
# FIND FORM
# ============================================================

soup = BeautifulSoup(
    page.text,
    "html.parser"
)

form = soup.find(
    "form"
)

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

FORM_ACTION_URL = urljoin(
    page.url,
    form_action
)


form_method = clean_text(
    form.get(
        "method",
        "post"
    )
).lower()


print(
    "Form method:",
    form_method,
    flush=True
)

print(
    "Form URL:",
    FORM_ACTION_URL,
    flush=True
)


# ============================================================
# FORM INPUTS
# ============================================================

base_form_data = {}


for inp in form.find_all(
    "input"
):

    name = inp.get(
        "name"
    )

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
        "image",

    ]:

        continue


    if input_type in [

        "checkbox",
        "radio",

    ]:

        if not inp.has_attr(
            "checked"
        ):

            continue


    base_form_data[name] = inp.get(
        "value",
        ""
    )


# ============================================================
# SELECT
# ============================================================

for select in form.find_all(
    "select"
):

    name = select.get(
        "name"
    )

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

        base_form_data[name] = (
            selected.get(
                "value",
                selected.get_text(
                    strip=True
                )
            )
        )


# ============================================================
# SUBMIT
# ============================================================

submit_fields = {}


for element in form.find_all(
    ["input", "button"]
):

    element_type = element.get(
        "type",
        ""
    ).lower()

    name = element.get(
        "name"
    )


    if (

        element_type == "submit"

        and name

    ):

        submit_fields[name] = (
            element.get(
                "value",
                element.get_text(
                    strip=True
                )
            )
        )


if not submit_fields:

    submit_fields = {

        "button2":
            "Submit"

    }


print(
    "Submit fields:",
    submit_fields,
    flush=True
)


# ============================================================
# COUNTERS
# ============================================================

processed = 0

successful = 0

not_found = 0

errors = 0


# ============================================================
# COLLECTION
# ============================================================

for group_name, roll_number in generate_rolls():

    roll = str(
        roll_number
    )


    # --------------------------------------------------------
    # SKIP EXISTING
    # --------------------------------------------------------

    if roll in existing_rolls:

        continue


    # --------------------------------------------------------
    # BATCH
    # --------------------------------------------------------

    if processed >= BATCH_SIZE:

        break


    processed += 1


    print(
        "\n" + "-" * 70,
        flush=True
    )

    print(
        f"[{processed}/{BATCH_SIZE}] "
        f"{group_name} | Roll: {roll}",
        flush=True
    )


    # ========================================================
    # FORM DATA
    # ========================================================

    form_data = dict(
        base_form_data
    )

    form_data["roll"] = roll


    for key, value in (
        submit_fields.items()
    ):

        form_data[key] = value


    # ========================================================
    # REQUEST
    # ========================================================

    print(
        f"REQUEST START: {roll}",
        flush=True
    )


    try:

        response = session.post(

            FORM_ACTION_URL,

            data=form_data,

            headers={

                "Referer":
                    page.url,

                "Origin":
                    "https://sresult.bise-ctg.gov.bd",

                "Content-Type":
                    "application/x-www-form-urlencoded",

            },

            timeout=
                REQUEST_TIMEOUT,

            allow_redirects=True,

        )


    except requests.exceptions.Timeout:

        print(
            f"TIMEOUT: {roll}",
            flush=True
        )

        errors += 1

        continue


    except requests.exceptions.RequestException as e:

        print(
            f"REQUEST ERROR: "
            f"{roll} -> {e}",
            flush=True
        )

        errors += 1

        continue


    print(
        f"REQUEST DONE: {roll} | "
        f"HTTP {response.status_code}",
        flush=True
    )


    # ========================================================
    # HTTP ERROR
    # ========================================================

    if response.status_code >= 400:

        errors += 1

        continue


    # ========================================================
    # PARSE
    # ========================================================

    print(
        f"PARSING: {roll}",
        flush=True
    )


    try:

        parsed = parse_result(

            response.text,

            roll,

            group_name

        )


    except Exception as e:

        print(
            f"PARSING ERROR: "
            f"{roll} -> {e}",
            flush=True
        )

        errors += 1

        continue


    print(
        f"PARSING DONE: {roll}",
        flush=True
    )


    # ========================================================
    # NOT FOUND
    # ========================================================

    if not parsed.get(
        "institute"
    ):

        print(
            "No result found.",
            flush=True
        )

        not_found += 1

        failed_rolls.append({

            "roll":
                roll,

            "group":
                group_name

        })


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
        parsed.get(
            "name",
            ""
        ),
        flush=True
    )

    print(
        "Institute:",
        parsed.get(
            "institute",
            ""
        ),
        flush=True
    )

    print(
        "District:",
        parsed.get(
            "district",
            ""
        ),
        flush=True
    )

    print(
        "GPA:",
        parsed.get(
            "gpa"
        ),
        flush=True
    )

    print(
        "Total Score:",
        parsed.get(
            "total_score"
        ),
        flush=True
    )

    print(
        "Subjects:",
        len(
            parsed.get(
                "subjects",
                []
            )
        ),
        flush=True
    )


    # ========================================================
    # SHOW SUBJECT MARKS
    # ========================================================

    for subject in parsed.get(
        "subjects",
        []
    ):

        print(
            "  SUBJECT:",
            subject.get(
                "code"
            ),
            "|",
            subject.get(
                "subject"
            ),
            "| Mark:",
            subject.get(
                "mark"
            ),
            "| Grade:",
            subject.get(
                "grade"
            ),
            "| Optional:",
            subject.get(
                "optional"
            ),
            flush=True
        )


    # ========================================================
    # SAVE MEMORY
    # ========================================================

    if roll not in existing_rolls:

        students.append(
            parsed
        )

        existing_rolls.add(
            roll
        )

        successful += 1


    # ========================================================
    # CHECKPOINT
    # ========================================================

    if (

        successful > 0

        and successful % SAVE_EVERY == 0

    ):

        print(
            "\nSaving checkpoint...",
            flush=True
        )


        save_json(
            "students.json",
            students
        )


        save_json(
            "failed_rolls.json",
            failed_rolls
        )


        print(
            "Checkpoint saved.",
            flush=True
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
# FINAL SAVE
# ============================================================

print(
    "\nSaving final checkpoint...",
    flush=True
)


save_json(
    "students.json",
    students
)


save_json(
    "failed_rolls.json",
    failed_rolls
)


# ============================================================
# SUMMARY
# ============================================================

remaining = max(

    total_target -
    len(existing_rolls),

    0

)


summary = {

    "year":
        YEAR,

    "board":
        BOARD,

    "target_rolls":
        total_target,

    "collected_total":
        len(students),

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

    "batch_size":
        BATCH_SIZE,

    "save_every":
        SAVE_EVERY,

    "roll_ranges":
        ROLL_RANGES,

}


save_json(
    "student_collection_summary.json",
    summary
)


# ============================================================
# FINAL OUTPUT
# ============================================================

print(
    "\n" + "=" * 70,
    flush=True
)

print(
    "SSC COLLECTION BATCH COMPLETE",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Processed this run:",
    processed,
    flush=True
)

print(
    "Successful:",
    successful,
    flush=True
)

print(
    "Not found:",
    not_found,
    flush=True
)

print(
    "Errors:",
    errors,
    flush=True
)

print(
    "Total students saved:",
    len(students),
    flush=True
)

print(
    "Remaining:",
    remaining,
    flush=True
)

print(
    "Students file:",
    STUDENTS_FILE,
    flush=True
)

print(
    "Summary file:",
    SUMMARY_FILE,
    flush=True
)

print(
    "Failed file:",
    FAILED_FILE,
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "DONE",
    flush=True
)