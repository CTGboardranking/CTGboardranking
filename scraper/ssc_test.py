import os
import json
import time
import random
import re

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ============================================================
# SUPABASE
# ============================================================

try:
    from supabase import create_client
except ImportError:
    create_client = None


# ============================================================
# SSC 2026 STUDENT COLLECTOR
#
# VERSION:
#
# - New students are collected
# - Existing COMPLETE students are skipped
# - Existing INCOMPLETE students are recollected
# - Missing marks/grades are repaired
# - Complete new data replaces incomplete old data
# - Incomplete new data does NOT destroy better old data
# - REQUIRED_SUBJECT_CODES = set()
# - All FOUND subjects are automatically checked
# - F grade without mark is considered complete
# - Supports combined values such as 184(A+)
# - Supabase pagination
# - Duplicate roll protection
# - Local checkpoint
# - Retry temporary request errors
# ============================================================


# ============================================================
# URL
# ============================================================

BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/"
)

INDIVIDUAL_URL = (
    BASE_URL + "individual/"
)


# ============================================================
# LOCAL FILES
# ============================================================

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


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_TABLE = os.getenv(
    "SUPABASE_TABLE",
    "students"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
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
# SETTINGS
# ============================================================

BATCH_SIZE = 10000

SAVE_EVERY = 100

MIN_DELAY = 0.1

MAX_DELAY = 0.2

REQUEST_TIMEOUT = (
    5,
    15
)

MAX_RETRIES = 2

SUPABASE_PAGE_SIZE = 1000

YEAR = 2026

BOARD = "Chattogram Board"


# ============================================================
# REQUIRED SUBJECT CODES
#
# IMPORTANT:
#
# Empty set means:
#
# NO fixed subject is mandatory.
#
# Every subject actually found on the result page
# is automatically checked.
#
# Example:
#
# 101, 107, 109, 150, 111, etc.
#
# are all checked automatically.
# ============================================================

REQUIRED_SUBJECT_CODES = set()


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
    "=" * 70,
    flush=True
)

print(
    "SSC 2026 STUDENT COLLECTOR",
    flush=True
)

print(
    "INCOMPLETE DATA RE-COLLECTION VERSION",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Batch size:",
    BATCH_SIZE,
    flush=True
)

print(
    "Save every:",
    SAVE_EVERY,
    flush=True
)

print(
    "Delay:",
    MIN_DELAY,
    "-",
    MAX_DELAY,
    flush=True
)

print(
    "Max retries:",
    MAX_RETRIES,
    flush=True
)

print(
    "Required subject codes: "
    "NONE - AUTO CHECK ALL FOUND SUBJECTS",
    flush=True
)

print(
    "=" * 70,
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
# SUPABASE CONNECTION
# ============================================================

if create_client is None:

    raise SystemExit(
        "Supabase package is not installed."
    )


if not SUPABASE_URL or not SUPABASE_KEY:

    raise SystemExit(
        "SUPABASE_URL / SUPABASE_KEY not configured."
    )


try:

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

except Exception as e:

    raise SystemExit(
        f"Supabase connection error: {e}"
    )


print(
    "Supabase: CONNECTED",
    flush=True
)

print(
    "Supabase table:",
    SUPABASE_TABLE,
    flush=True
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
# GRADE
# ============================================================

GRADE_PATTERN = re.compile(
    r"^(A\+|A-|A|B|C|D|F)$",
    re.I
)


def normalize_grade(value):

    value = clean_text(value)

    if not value:
        return ""

    value = value.replace(
        "(",
        ""
    ).replace(
        ")",
        ""
    )

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

    for value in values:

        value = clean_text(value)

        if not value:
            continue

        normalized = value.upper()

        normalized = normalized.replace(
            " ",
            ""
        )


        # ----------------------------------------------------
        # 184(A+)
        #
        # IMPORTANT:
        # SSC result pages can contain marks above 100
        # because some subjects have combined/full marks.
        #
        # Accept up to 300 here.
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

            if 0 <= number <= 300:

                return (
                    number,
                    match.group(2).upper()
                )


        # ----------------------------------------------------
        # 184A+
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

            if 0 <= number <= 300:

                return (
                    number,
                    match.group(2).upper()
                )


        # ----------------------------------------------------
        # Grade only
        # ----------------------------------------------------

        grade_only = normalize_grade(
            normalized
        )

        if grade_only:

            grade = grade_only

            continue


        # ----------------------------------------------------
        # (A+)
        # ----------------------------------------------------

        match = re.fullmatch(
            r"\("
            r"(A\+|A-|A|B|C|D|F)"
            r"\)",
            normalized,
            re.I
        )

        if match:

            grade = match.group(1).upper()

            continue


        # ----------------------------------------------------
        # Mark only
        # ----------------------------------------------------

        if re.fullmatch(
            r"\d{1,3}",
            normalized
        ):

            number = int(
                normalized
            )

            if 0 <= number <= 300:

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


            mark, grade = (
                parse_subject_values(
                    values[2:]
                )
            )


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
# SUBJECT COMPLETENESS
# ============================================================

def is_subject_complete(subject):

    if not isinstance(
        subject,
        dict
    ):

        return False


    mark = subject.get(
        "mark"
    )

    grade = normalize_grade(
        subject.get(
            "grade",
            ""
        )
    )


    # --------------------------------------------------------
    # NORMAL SUBJECT
    #
    # Mark + Grade required
    # --------------------------------------------------------

    if grade and grade != "F":

        mark_valid = (

            mark is not None

            and

            str(mark).strip() != ""

        )


        return (
            mark_valid
            and
            bool(grade)
        )


    # --------------------------------------------------------
    # FAILED SUBJECT
    #
    # If the official result says F, mark may legitimately
    # be unavailable on the page.
    #
    # Therefore:
    #
    # F + no mark = COMPLETE
    # F + mark = COMPLETE
    # --------------------------------------------------------

    if grade == "F":

        return True


    # --------------------------------------------------------
    # No grade
    # --------------------------------------------------------

    return False


# ============================================================
# STUDENT COMPLETENESS
# ============================================================

def get_missing_subjects(
    student
):

    subjects = student.get(
        "subjects",
        []
    )


    if not isinstance(
        subjects,
        list
    ):

        return [
            "subjects"
        ]


    # ========================================================
    # REQUIRED SUBJECT MODE
    #
    # This block is only used if specific codes are supplied.
    # Currently REQUIRED_SUBJECT_CODES = set()
    # ========================================================

    if REQUIRED_SUBJECT_CODES:

        missing = []

        found_required = set()


        for subject in subjects:

            if not isinstance(
                subject,
                dict
            ):

                continue


            code = str(
                subject.get(
                    "code",
                    ""
                )
            ).strip()


            if code in REQUIRED_SUBJECT_CODES:

                found_required.add(
                    code
                )

                if not is_subject_complete(
                    subject
                ):

                    missing.append(
                        code
                    )


        for code in REQUIRED_SUBJECT_CODES:

            if code not in found_required:

                missing.append(
                    code
                )


        return sorted(
            set(missing)
        )


    # ========================================================
    # AUTO SUBJECT MODE
    #
    # REQUIRED_SUBJECT_CODES = set()
    #
    # Every subject found on the result is checked.
    #
    # No subjects at all = incomplete.
    # ========================================================

    if not subjects:

        return [
            "subjects"
        ]


    missing = []


    for subject in subjects:

        if not isinstance(
            subject,
            dict
        ):

            missing.append(
                "invalid_subject"
            )

            continue


        code = str(
            subject.get(
                "code",
                ""
            )
        ).strip()


        if not code:

            missing.append(
                "unknown_subject"
            )

            continue


        if not is_subject_complete(
            subject
        ):

            missing.append(
                code
            )


    return sorted(
        set(missing)
    )


def is_student_complete(
    student
):

    missing = get_missing_subjects(
        student
    )

    return len(missing) == 0


# ============================================================
# TOTAL MARKS
# ============================================================

def calculate_total_score(
    subjects
):

    total = 0

    found = False

    for subject in subjects:

        if not isinstance(
            subject,
            dict
        ):

            continue


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
                match.group(1).upper()
            )


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
    # FALLBACK RESULT
    # ========================================================

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )


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
    # RESULT FALLBACK
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
    # VALID RESULT
    # ========================================================

    has_data = (

        bool(
            result["name"]
        )

        or

        bool(
            result["institute"]
        )

        or

        len(
            result["subjects"]
        ) > 0

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
# LOAD LOCAL DATA
# ============================================================

students = load_json(
    "students.json",
    []
)

failed_rolls = load_json(
    "failed_rolls.json",
    []
)

attempted_rolls = load_json(
    "attempted_rolls.json",
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


if not isinstance(
    attempted_rolls,
    list
):

    attempted_rolls = []


# ============================================================
# LOCAL STUDENT MAP
# ============================================================

local_students = {}

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

        local_students[roll] = student


# ============================================================
# SUPABASE STUDENT MAP
# ============================================================

def load_supabase_students():

    print(
        "",
        flush=True
    )

    print(
        "Loading existing Supabase students...",
        flush=True
    )


    result = {}

    offset = 0


    while True:

        try:

            response = (

                supabase

                .table(
                    SUPABASE_TABLE
                )

                .select(
                    "*"
                )

                .range(
                    offset,
                    offset +
                    SUPABASE_PAGE_SIZE -
                    1
                )

                .execute()

            )


        except Exception as e:

            print(
                "Supabase load error:",
                e,
                flush=True
            )

            raise SystemExit(
                "Could not load Supabase students."
            )


        rows = response.data or []


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

                result[roll] = row


        print(
            "Loaded Supabase rows:",
            len(result),
            flush=True
        )


        if len(rows) < SUPABASE_PAGE_SIZE:

            break


        offset += SUPABASE_PAGE_SIZE


    print(
        "",
        flush=True
    )

    print(
        "Supabase total:",
        len(result),
        flush=True
    )


    return result


supabase_students = (
    load_supabase_students()
)


# ============================================================
# FIND INCOMPLETE SUPABASE STUDENTS
# ============================================================

incomplete_supabase = {}

complete_supabase = {}

for roll, student in supabase_students.items():

    if is_student_complete(
        student
    ):

        complete_supabase[roll] = student

    else:

        incomplete_supabase[roll] = student


print(
    "",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "SUPABASE DATA STATUS",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Total Supabase:",
    len(supabase_students),
    flush=True
)

print(
    "Complete:",
    len(complete_supabase),
    flush=True
)

print(
    "Incomplete:",
    len(incomplete_supabase),
    flush=True
)

print(
    "=" * 70,
    flush=True
)


# ============================================================
# SHOW INCOMPLETE EXAMPLES
# ============================================================

print(
    "",
    flush=True
)

print(
    "Incomplete examples:",
    flush=True
)


for index, (
    roll,
    student
) in enumerate(
    incomplete_supabase.items()
):

    if index >= 20:
        break


    missing = get_missing_subjects(
        student
    )


    print(
        roll,
        "|",
        student.get(
            "name",
            ""
        ),
        "| Missing:",
        ",".join(missing),
        flush=True
    )


# ============================================================
# FAILED SET
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
# TARGET ROLLS
#
# 1. Existing incomplete students
# 2. New students not in Supabase
#
# Complete existing students are skipped.
# ============================================================

target_rolls = []


for group_name, roll_number in generate_rolls():

    roll = str(
        roll_number
    )


    if roll in incomplete_supabase:

        target_rolls.append(
            (
                group_name,
                roll
            )
        )

        continue


    if roll not in supabase_students:

        target_rolls.append(
            (
                group_name,
                roll
            )

        )


# ============================================================
# TARGET LIMIT
# ============================================================

total_targets = len(
    target_rolls
)

run_targets = target_rolls[
    :BATCH_SIZE
]


# ============================================================
# TARGET INFO
# ============================================================

print(
    "",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "COLLECTION TARGET",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Incomplete existing:",
    len(incomplete_supabase),
    flush=True
)

print(
    "New students:",
    sum(
        1
        for group, roll in target_rolls
        if roll not in supabase_students
    ),
    flush=True
)

print(
    "Total targets:",
    total_targets,
    flush=True
)

print(
    "This run:",
    len(run_targets),
    flush=True
)

print(
    "Remaining after this batch:",
    max(
        total_targets -
        len(run_targets),
        0
    ),
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
        and
        name
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

repaired = 0

new_students = 0

still_incomplete = 0

not_found = 0

errors = 0

temporary_request_errors = 0

supabase_saved = 0

supabase_errors = 0


# ============================================================
# MERGE SUBJECTS
# ============================================================

def merge_subjects(
    old_subjects,
    new_subjects
):

    old_map = {}

    new_map = {}


    for subject in old_subjects or []:

        if not isinstance(
            subject,
            dict
        ):

            continue


        code = str(
            subject.get(
                "code",
                ""
            )
        ).strip()


        if code:

            old_map[code] = subject


    for subject in new_subjects or []:

        if not isinstance(
            subject,
            dict
        ):

            continue


        code = str(
            subject.get(
                "code",
                ""
            )
        ).strip()


        if code:

            new_map[code] = subject


    merged = {}


    all_codes = (
        set(old_map)
        |
        set(new_map)
    )


    for code in all_codes:

        old = old_map.get(
            code
        )

        new = new_map.get(
            code
        )


        if old is None:

            merged[code] = new

            continue


        if new is None:

            merged[code] = old

            continue


        old_complete = (
            is_subject_complete(
                old
            )
        )

        new_complete = (
            is_subject_complete(
                new
            )
        )


        if new_complete:

            merged[code] = new

        elif old_complete:

            merged[code] = old

        else:

            # ------------------------------------------------
            # Merge partial information.
            #
            # If old has mark and new has grade,
            # keep both.
            # ------------------------------------------------

            merged_subject = dict(
                old
            )


            old_mark = old.get(
                "mark"
            )

            new_mark = new.get(
                "mark"
            )

            old_grade = normalize_grade(
                old.get(
                    "grade",
                    ""
                )
            )

            new_grade = normalize_grade(
                new.get(
                    "grade",
                    ""
                )
            )


            if (
                old_mark is None
                and
                new_mark is not None
            ):

                merged_subject["mark"] = (
                    new_mark
                )


            if (
                not old_grade
                and
                new_grade
            ):

                merged_subject["grade"] = (
                    new_grade
                )


            if not merged_subject.get(
                "subject"
            ):

                merged_subject["subject"] = (
                    new.get(
                        "subject",
                        ""
                    )
                )


            if (
                "optional" not in merged_subject
                and
                "optional" in new
            ):

                merged_subject["optional"] = (
                    new["optional"]
                )


            merged[code] = merged_subject


    return list(
        merged.values()
    )


# ============================================================
# UPSERT
# ============================================================

def supabase_upsert_student(
    student
):

    try:

        roll = str(
            student.get(
                "roll",
                ""
            )
        ).strip()


        if not roll:

            return (
                False,
                "Missing roll"
            )


        payload = {

            "roll":
                roll,

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

            "father_name":
                student.get(
                    "father_name",
                    ""
                ),

            "mother_name":
                student.get(
                    "mother_name",
                    ""
                ),

            "session":
                student.get(
                    "session",
                    ""
                ),

            "reg_no":
                student.get(
                    "reg_no",
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


        (
            supabase

            .table(
                SUPABASE_TABLE
            )

            .upsert(
                payload,
                on_conflict="roll"
            )

            .execute()
        )


        return (
            True,
            "Upsert successful"
        )


    except Exception as e:

        return (
            False,
            str(e)
        )


# ============================================================
# COLLECTION LOOP
# ============================================================

for group_name, roll in run_targets:

    processed += 1


    old_student = (
        supabase_students.get(
            roll
        )
    )


    is_repair = (
        old_student is not None
        and
        not is_student_complete(
            old_student
        )
    )


    print(
        "",
        flush=True
    )

    print(
        "-" * 70,
        flush=True
    )

    print(
        f"[{processed}/{len(run_targets)}] "
        f"{group_name} | Roll: {roll}",
        flush=True
    )


    if is_repair:

        missing = get_missing_subjects(
            old_student
        )


        print(
            "MODE: REPAIR",
            flush=True
        )

        print(
            "Missing:",
            ", ".join(missing),
            flush=True
        )

    else:

        print(
            "MODE: NEW",
            flush=True
        )


    attempted_rolls.append(
        roll
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

    request_success = False


    for attempt in range(
        MAX_RETRIES + 1
    ):

        try:

            print(
                f"REQUEST START: "
                f"{roll} "
                f"(attempt {attempt + 1})",
                flush=True
            )


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


            print(
                f"REQUEST DONE: "
                f"{roll} | "
                f"HTTP {response.status_code}",
                flush=True
            )


            if response.status_code < 400:

                request_success = True

                break


        except requests.exceptions.Timeout:

            print(
                f"TIMEOUT: {roll}",
                flush=True
            )


        except requests.exceptions.RequestException as e:

            print(
                f"REQUEST ERROR: "
                f"{roll} -> {e}",
                flush=True
            )


        if attempt < MAX_RETRIES:

            retry_delay = random.uniform(
                1.0,
                2.0
            )


            print(
                f"Retrying in "
                f"{retry_delay:.1f}s...",
                flush=True
            )


            time.sleep(
                retry_delay
            )


    # ========================================================
    # REQUEST FAILED
    # ========================================================

    if not request_success:

        errors += 1

        temporary_request_errors += 1

        print(
            f"REQUEST FAILED: {roll}",
            flush=True
        )

        continue


    # ========================================================
    # PARSE
    # ========================================================

    try:

        parsed = parse_result(

            response.text,

            roll,

            group_name

        )


    except Exception as e:

        errors += 1

        print(
            f"PARSING ERROR: "
            f"{roll} -> {e}",
            flush=True
        )

        continue


    # ========================================================
    # NOT FOUND
    # ========================================================

    if parsed is None:

        not_found += 1

        print(
            "No valid result detected.",
            flush=True
        )

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


        continue


    # ========================================================
    # MERGE WITH OLD DATA
    # ========================================================

    if old_student:

        old_subjects = (
            old_student.get(
                "subjects",
                []
            )
        )


        parsed["subjects"] = (
            merge_subjects(
                old_subjects,
                parsed.get(
                    "subjects",
                    []
                )
            )
        )


        # ----------------------------------------------------
        # Preserve old values if new page omitted them
        # ----------------------------------------------------

        for key in [

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
            "gpa",

        ]:

            new_value = parsed.get(
                key
            )

            old_value = old_student.get(
                key
            )


            if (
                (
                    new_value is None
                    or
                    str(new_value).strip() == ""
                )
                and
                old_value not in (
                    None,
                    ""
                )
            ):

                parsed[key] = old_value


        parsed["total_score"] = (
            calculate_total_score(
                parsed["subjects"]
            )
        )


    # ========================================================
    # CHECK COMPLETENESS
    # ========================================================

    missing = get_missing_subjects(
        parsed
    )


    print(
        "",
        flush=True
    )

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
            flush=True
        )


    # ========================================================
    # STILL INCOMPLETE
    # ========================================================

    if missing:

        still_incomplete += 1


        print(
            "",
            flush=True
        )

        print(
            "⚠ STILL INCOMPLETE:",
            ", ".join(missing),
            flush=True
        )


        # ----------------------------------------------------
        # Existing student
        # ----------------------------------------------------

        if old_student:

            old_missing = get_missing_subjects(
                old_student
            )


            improvement = (
                len(missing)
                <
                len(old_missing)
            )


            if improvement:

                print(
                    "Improved incomplete record. "
                    "Saving partial repair.",
                    flush=True
                )


                supabase_ok, message = (
                    supabase_upsert_student(
                        parsed
                    )
                )


                if supabase_ok:

                    supabase_saved += 1

                    repaired += 1

                    supabase_students[roll] = (
                        parsed
                    )

                else:

                    supabase_errors += 1

                    print(
                        "SUPABASE ERROR:",
                        message,
                        flush=True
                    )


            else:

                print(
                    "No improvement. "
                    "Keeping existing record.",
                    flush=True
                )


        # ----------------------------------------------------
        # New student
        # ----------------------------------------------------

        else:

            print(
                "New record is incomplete. "
                "Saving for future repair.",
                flush=True
            )


            supabase_ok, message = (
                supabase_upsert_student(
                    parsed
                )
            )


            if supabase_ok:

                supabase_saved += 1

                new_students += 1

                supabase_students[roll] = (
                    parsed
                )

            else:

                supabase_errors += 1

                print(
                    "SUPABASE ERROR:",
                    message,
                    flush=True
                )


        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )


        continue


    # ========================================================
    # COMPLETE DATA
    # ========================================================

    print(
        "",
        flush=True
    )

    print(
        "✓ COMPLETE DATA",
        flush=True
    )


    # ========================================================
    # SUPABASE UPSERT
    # ========================================================

    supabase_ok, message = (
        supabase_upsert_student(
            parsed
        )
    )


    if not supabase_ok:

        supabase_errors += 1

        print(
            "SUPABASE ERROR:",
            message,
            flush=True
        )

        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )

        continue


    supabase_saved += 1

    successful += 1


    if is_repair:

        repaired += 1

        print(
            "✓ REPAIRED:",
            roll,
            flush=True
        )

    else:

        new_students += 1

        print(
            "✓ NEW STUDENT SAVED:",
            roll,
            flush=True
        )


    # ========================================================
    # UPDATE LOCAL MAP
    # ========================================================

    local_students[roll] = parsed

    supabase_students[roll] = parsed


    # ========================================================
    # UPDATE STUDENTS JSON
    # ========================================================

    found_local = False


    for index, student in enumerate(
        students
    ):

        if str(
            student.get(
                "roll",
                ""
            )
        ).strip() == roll:

            students[index] = parsed

            found_local = True

            break


    if not found_local:

        students.append(
            parsed
        )


    # ========================================================
    # CHECKPOINT
    # ========================================================

    if (
        processed % SAVE_EVERY == 0
    ):

        print(
            "",
            flush=True
        )

        print(
            "Saving checkpoint...",
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


        save_json(
            "attempted_rolls.json",
            attempted_rolls
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
    "",
    flush=True
)

print(
    "Saving final checkpoint...",
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


save_json(
    "attempted_rolls.json",
    attempted_rolls
)


# ============================================================
# FINAL COUNTS
# ============================================================

final_supabase_count = len(
    supabase_students
)


remaining_incomplete = sum(

    1

    for student
    in supabase_students.values()

    if not is_student_complete(
        student
    )

)


# ============================================================
# SUMMARY
# ============================================================

summary = {

    "year":
        YEAR,

    "board":
        BOARD,

    "total_supabase_before":
        len(supabase_students),

    "incomplete_before":
        len(incomplete_supabase),

    "target_total":
        total_targets,

    "processed_this_run":
        processed,

    "successful_complete":
        successful,

    "repaired_this_run":
        repaired,

    "new_students_this_run":
        new_students,

    "still_incomplete_this_run":
        still_incomplete,

    "not_found_this_run":
        not_found,

    "errors_this_run":
        errors,

    "temporary_request_errors":
        temporary_request_errors,

    "supabase_saved_this_run":
        supabase_saved,

    "supabase_errors_this_run":
        supabase_errors,

    "supabase_total_after":
        final_supabase_count,

    "remaining_incomplete":
        remaining_incomplete,

    "batch_size":
        BATCH_SIZE,

    "required_subject_codes":
        sorted(
            REQUIRED_SUBJECT_CODES
        ),

    "auto_check_all_found_subjects":
        not bool(
            REQUIRED_SUBJECT_CODES
        ),

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
    "",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "SSC COLLECTION / REPAIR COMPLETE",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Processed:",
    processed,
    flush=True
)

print(
    "Successful complete:",
    successful,
    flush=True
)

print(
    "Repaired:",
    repaired,
    flush=True
)

print(
    "New students:",
    new_students,
    flush=True
)

print(
    "Still incomplete:",
    still_incomplete,
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
    "Supabase saved:",
    supabase_saved,
    flush=True
)

print(
    "Supabase errors:",
    supabase_errors,
    flush=True
)

print(
    "Supabase total:",
    final_supabase_count,
    flush=True
)

print(
    "Remaining incomplete:",
    remaining_incomplete,
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