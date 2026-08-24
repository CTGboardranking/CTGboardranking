import os
import json
import time
import random
import re

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ============================================================
# SSC 2026 STUDENT COLLECTOR - FINAL VERSION
# ============================================================

BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/"
)

INDIVIDUAL_URL = (
    BASE_URL + "individual/"
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

BATCH_SIZE = 10000

SAVE_EVERY = 500

MIN_DELAY = 0.1

MAX_DELAY = 0.2

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
# STARTUP
# ============================================================

print(
    "========================================",
    flush=True
)

print(
    "SSC STUDENT COLLECTOR - FINAL VERSION",
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
    "BATCH_SIZE:",
    BATCH_SIZE,
    flush=True
)

print(
    "SAVE_EVERY:",
    SAVE_EVERY,
    flush=True
)

print(
    "========================================",
    flush=True
)


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

                gpa = float(
                    match.group(1)
                )

                if 0 <= gpa <= 5:
                    return gpa

            except Exception:
                pass

    return None


# ============================================================
# FIND GPA
# ============================================================

def find_page_gpa(soup):

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

                gpa = float(
                    match.group(1)
                )

                if 0 <= gpa <= 5:
                    return gpa

            except Exception:
                pass


    # Search table cells
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

            if "GPA" in value.upper():

                gpa = parse_gpa(value)

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
# LABEL VALUE
# ============================================================

def find_value_after_label(
    values,
    label
):

    label = label.lower().strip()

    for i, value in enumerate(values):

        current = clean_text(
            value
        ).lower()

        if current == label:

            if i + 1 < len(values):

                return clean_text(
                    values[i + 1]
                )

    return ""


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

        "CHITTAGONG":
            "Chattogram",

        "CHATTOGRAM":
            "Chattogram",

        "COX'S BAZAR":
            "Cox's Bazar",

        "COXS BAZAR":
            "Cox's Bazar",

        "COMILLA":
            "Cumilla",

        "CUMILLA":
            "Cumilla",

        "FENI":
            "Feni",

        "NOAKHALI":
            "Noakhali",

        "LAKSHMIPUR":
            "Lakshmipur",

        "CHANDPUR":
            "Chandpur",

        "BRAHMANBARIA":
            "Brahmanbaria",

        "RANGAMATI":
            "Rangamati",

        "KHAGRACHHARI":
            "Khagrachhari",

        "BANDARBAN":
            "Bandarban",
    }

    upper = institute.upper()

    for key, district in known.items():

        if key in upper:
            return district

    return ""


# ============================================================
# SUBJECT GRADE
# ============================================================

GRADE_PATTERN = re.compile(
    r"^(A\+|A-|A|B|C|D|F)$",
    re.I
)


def normalize_grade(value):

    value = clean_text(value)

    if not value:
        return ""

    # Remove brackets
    value = value.replace(
        "(",
        ""
    ).replace(
        ")",
        ""
    )

    # Fix spaces
    value = value.replace(
        " ",
        ""
    )

    value = value.upper()

    if GRADE_PATTERN.fullmatch(
        value
    ):
        return value

    return ""


# ============================================================
# SUBJECT MARK + GRADE
# ============================================================

def parse_subject_values(values):

    mark = None

    grade = ""

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Actual result page can contain:
    #
    # 086(C)
    # 083(C)
    # (F)
    # 068(A-)
    # 033(A-)
    #
    # So parse each cell independently.
    # --------------------------------------------------------

    for value in values:

        value = clean_text(value)

        if not value:
            continue

        # ----------------------------------------------------
        # Remove extra spaces
        # ----------------------------------------------------

        normalized = value.upper()

        normalized = normalized.replace(
            " ",
            ""
        )

        # ----------------------------------------------------
        # Mark + grade
        # Examples:
        #
        # 086(C)
        # 83(C)
        # 068(A-)
        # 95(A+)
        # ----------------------------------------------------

        match = re.fullmatch(
            r"(\d{1,3})"
            r"\("
            r"(A\+|A-|A|B|C|D|F)"
            r"\)",
            normalized,
            re.I
        )

        if match:

            number = int(
                match.group(1)
            )

            if 0 <= number <= 100:

                mark = number

                grade = (
                    match.group(2)
                    .upper()
                )

                return (
                    mark,
                    grade
                )


        # ----------------------------------------------------
        # Mark + grade without brackets
        # ----------------------------------------------------

        match = re.fullmatch(
            r"(\d{1,3})"
            r"(A\+|A-|A|B|C|D|F)",
            normalized,
            re.I
        )

        if match:

            number = int(
                match.group(1)
            )

            if 0 <= number <= 100:

                mark = number

                grade = (
                    match.group(2)
                    .upper()
                )

                return (
                    mark,
                    grade
                )


        # ----------------------------------------------------
        # Grade only
        #
        # (F)
        # (A-)
        # ----------------------------------------------------

        grade_only = normalize_grade(
            normalized
        )

        if grade_only:

            grade = grade_only

            continue


        # ----------------------------------------------------
        # Grade inside brackets
        # ----------------------------------------------------

        match = re.fullmatch(
            r"\((A\+|A-|A|B|C|D|F)\)",
            normalized,
            re.I
        )

        if match:

            grade = (
                match.group(1)
                .upper()
            )

            continue


        # ----------------------------------------------------
        # Plain numeric mark
        # ----------------------------------------------------

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


# ============================================================
# SUBJECT PARSER
# ============================================================

def parse_subjects(soup):

    subjects = []

    seen = set()

    for table in soup.find_all(
        "table"
    ):

        for row in table.find_all(
            "tr"
        ):

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

            # ------------------------------------------------
            # Subject code must be numeric
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Parse mark + grade
            # ------------------------------------------------

            mark, grade = (
                parse_subject_values(
                    values[2:]
                )
            )


            # ------------------------------------------------
            # Optional subject detection
            # ------------------------------------------------

            combined = " ".join(
                values
            ).upper()

            optional = (
                "OPTIONAL" in combined
                or
                "4TH SUBJECT" in combined
                or
                "FOURTH SUBJECT" in combined
            )


            subjects.append({

                "code":
                    code,

                "subject":
                    subject_name,

                "mark":
                    mark,

                "grade":
                    grade,

                "optional":
                    optional,

            })

    return subjects


# ============================================================
# TOTAL MARKS
# ============================================================

def calculate_total_score(
    subjects
):

    total = 0

    found = False

    for subject in subjects:

        mark = subject.get(
            "mark"
        )

        if isinstance(
            mark,
            int
        ):

            total += mark

            found = True

    if found:
        return total

    return None


# ============================================================
# RESULT STATUS
# ============================================================

def detect_result(
    soup,
    subjects
):

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    upper = page_text.upper()


    # --------------------------------------------------------
    # Direct official result
    # --------------------------------------------------------

    patterns = [

        r"\bRESULT\s*[:\-]\s*(PASS|FAIL)\b",

        r"\bFINAL\s+RESULT\s*[:\-]?\s*"
        r"(PASS|FAIL)\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            return (
                match.group(1)
                .upper()
            )


    # --------------------------------------------------------
    # Search table rows
    # --------------------------------------------------------

    for row in soup.find_all(
        "tr"
    ):

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

        joined = " ".join(
            values
        ).upper()

        if "RESULT" in joined:

            if re.search(
                r"\bPASS\b",
                joined
            ):
                return "PASS"

            if re.search(
                r"\bFAIL\b",
                joined
            ):
                return "FAIL"


    # --------------------------------------------------------
    # If F grade exists => FAIL
    # --------------------------------------------------------

    for subject in subjects:

        grade = str(
            subject.get(
                "grade",
                ""
            )
        ).upper()

        if grade == "F":

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

        "roll":
            str(requested_roll),

        "name":
            "",

        "board":
            "",

        "group":
            group_name,

        "father_name":
            "",

        "mother_name":
            "",

        "session":
            "",

        "reg_no":
            "",

        "type":
            "",

        "institute":
            "",

        "district":
            "",

        "result":
            "",

        "date_of_birth":
            "",

        "gpa":
            None,

        "total_score":
            None,

        "subjects":
            [],

    }


    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    for row in soup.find_all(
        "tr"
    ):

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


        for label, key in fields:

            value = find_value_after_label(
                values,
                label
            )

            if value:

                result[key] = value


        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        result_value = (
            find_value_after_label(
                values,
                "Result"
            )
        )

        if result_value:

            result_value = clean_text(
                result_value
            ).upper()

            if result_value in (
                "PASS",
                "FAIL"
            ):

                result["result"] = (
                    result_value
                )


    # ========================================================
    # FALLBACK BASIC TEXT SEARCH
    # ========================================================

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )


    # --------------------------------------------------------
    # Result fallback
    # --------------------------------------------------------

    if not result["result"]:

        match = re.search(
            r"\bRESULT\s*[:\-]\s*"
            r"(PASS|FAIL)\b",
            page_text,
            re.I
        )

        if match:

            result["result"] = (
                match.group(1).upper()
            )


    # ========================================================
    # GPA
    # ========================================================

    result["gpa"] = find_page_gpa(
        soup
    )


    # ========================================================
    # SUBJECTS
    # ========================================================

    result["subjects"] = parse_subjects(
        soup
    )


    # ========================================================
    # RESULT FALLBACK FROM SUBJECTS
    # ========================================================

    if not result["result"]:

        result["result"] = detect_result(
            soup,
            result["subjects"]
        )


    # ========================================================
    # TOTAL SCORE
    # ========================================================

    result["total_score"] = (
        calculate_total_score(
            result["subjects"]
        )
    )


    # ========================================================
    # DISTRICT
    # ========================================================

    if not result["district"]:

        result["district"] = (
            extract_district_from_institute(
                result["institute"]
            )
        )


    # ========================================================
    # VALID RESULT CHECK
    # ========================================================

    # A real result page should have at least:
    # name OR institute OR subject data.

    has_data = (
        bool(result["name"])
        or
        bool(result["institute"])
        or
        len(result["subjects"]) > 0
    )


    if not has_data:

        return None


    # ========================================================
    # CLEAN STRINGS
    # ========================================================

    string_fields = [

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

    ]

    for key in string_fields:

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
# LOAD EXISTING STUDENTS
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

    if not isinstance(
        student,
        dict
    ):
        continue

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
# FAILED ROLLS
# ============================================================

failed_set = set()

for item in failed_rolls:

    if isinstance(
        item,
        dict
    ):

        roll = str(
            item.get(
                "roll",
                ""
            )
        ).strip()

    else:

        roll = str(
            item
        ).strip()

    if roll:

        failed_set.add(
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
# START INFO
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
    "Already failed:",
    len(failed_set),
    flush=True
)

print(
    "Remaining:",
    max(
        total_target
        -
        len(existing_rolls)
        -
        len(failed_set),
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
# SELECT INPUTS
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

skipped_failed = 0

skipped_existing = 0


# ============================================================
# COLLECTION LOOP
# ============================================================

for group_name, roll_number in generate_rolls():

    roll = str(
        roll_number
    )


    # --------------------------------------------------------
    # SKIP EXISTING
    # --------------------------------------------------------

    if roll in existing_rolls:

        skipped_existing += 1

        continue


    # --------------------------------------------------------
    # SKIP FAILED
    # --------------------------------------------------------

    if roll in failed_set:

        skipped_failed += 1

        continue


    # --------------------------------------------------------
    # BATCH LIMIT
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


    for key, value in submit_fields.items():

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

        # Do NOT mark timeout as permanently failed.
        # It can be retried on next run.

        continue


    except requests.exceptions.RequestException as e:

        print(
            f"REQUEST ERROR: {roll} -> {e}",
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

        print(
            f"HTTP ERROR: {roll}",
            flush=True
        )

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

    if parsed is None:

        print(
            "No valid result detected.",
            flush=True
        )

        not_found += 1


        failed_rolls.append({

            "roll":
                roll,

            "group":
                group_name,

            "reason":
                "No valid result",

        })


        failed_set.add(
            roll
        )


        # Save failed roll immediately
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
        "Result:",
        parsed.get(
            "result",
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
    # SUBJECT OUTPUT
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
    # SAVE STUDENT
    # ========================================================

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
        and
        successful % SAVE_EVERY == 0
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
# REMAINING
# ============================================================

remaining = max(

    total_target
    -
    len(existing_rolls)
    -
    len(failed_set),

    0

)


# ============================================================
# SUMMARY
# ============================================================

summary = {

    "year":
        YEAR,

    "board":
        BOARD,

    "target_rolls":
        total_target,

    "collected_total":
        len(students),

    "failed_total":
        len(failed_set),

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

    "skipped_existing":
        skipped_existing,

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
    "Skipped existing:",
    skipped_existing,
    flush=True
)

print(
    "Skipped failed:",
    skipped_failed,
    flush=True
)

print(
    "Total students saved:",
    len(students),
    flush=True
)

print(
    "Total failed/no-result:",
    len(failed_set),
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