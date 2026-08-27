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
# SSC 2026 FULL SUBJECT-WISE COLLECTOR
#
# FINAL RULE:
#
# 1. Supabase-এ roll নেই
#       -> COLLECT
#
# 2. Supabase-এ 12 unique subjects আছে
#    এবং প্রতিটির Mark + Grade আছে
#       -> SKIP
#
# 3. 12 subjects-এর মধ্যে 1/2/3... subject-এর
#    Mark বা Grade missing
#       -> FULL RESULT RE-COLLECT
#
# 4. F grade valid
#    কিন্তু Mark + F দুটোই থাকতে হবে
#
# 5. Incomplete old subjects-এর সাথে নতুন subjects
#    MERGE করা হবে না
#
# 6. নতুন collection পাওয়া গেলে পুরো subjects
#    নতুন data দিয়ে REPLACE হবে
#
# 7. একই run-এ duplicate roll process হবে না
#
# 8. Complete হয়ে গেলে পরবর্তী run-এ skip হবে
#
# 9. Cursor দিয়ে GitHub Actions restart/resume
#
# 10. Failed request permanent skip নয়
#
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

CURSOR_FILE = os.path.join(
    OUTPUT_DIR,
    "collection_cursor.json"
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

SAVE_EVERY = 500

MIN_DELAY = 0.10

MAX_DELAY = 0.20

REQUEST_TIMEOUT = (
    5,
    15
)

MAX_RETRIES = 2

SUPABASE_PAGE_SIZE = 1000

YEAR = 2026

BOARD = "Chattogram Board"

# ============================================================
# IMPORTANT
#
# প্রত্যেক শিক্ষার্থীর 12টি subject required.
# ============================================================

EXPECTED_SUBJECT_COUNT = 12


# ============================================================
# REQUIRED SUBJECT CODES
#
# Empty রাখলে 12টি পাওয়া subject-এর সবগুলো check হবে.
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
    "SSC 2026 FULL SUBJECT-WISE COLLECTOR",
    flush=True
)

print(
    "12 SUBJECT COMPLETE / REPAIR VERSION",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Expected subjects:",
    EXPECTED_SUBJECT_COUNT,
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
    "F grade:",
    "VALID ONLY WITH MARK + GRADE",
    flush=True
)

print(
    "Incomplete result:",
    "FULL RE-COLLECTION",
    flush=True
)

print(
    "Old incomplete subjects:",
    "NOT MERGED",
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
# CURSOR
# ============================================================

def load_cursor():

    data = load_json(
        "collection_cursor.json",
        {}
    )

    if not isinstance(
        data,
        dict
    ):

        return {
            "last_processed_roll": 0,
            "cycle": 1
        }

    try:

        last_roll = int(
            data.get(
                "last_processed_roll",
                0
            )
        )

    except Exception:

        last_roll = 0


    try:

        cycle = int(
            data.get(
                "cycle",
                1
            )
        )

    except Exception:

        cycle = 1


    return {

        "last_processed_roll":
            last_roll,

        "cycle":
            cycle

    }


def save_cursor(
    last_processed_roll,
    cycle
):

    save_json(
        "collection_cursor.json",
        {

            "last_processed_roll":
                int(last_processed_roll),

            "cycle":
                int(cycle),

            "updated_at":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        }
    )


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

    value = clean_text(
        value
    )

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

        value = clean_text(
            value
        )

        if not value:

            continue


        normalized = value.upper()

        normalized = normalized.replace(
            " ",
            ""
        )


        # ----------------------------------------------------
        # 184(A+)
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

            grade = (
                match.group(1).upper()
            )

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


            seen.add(
                key
            )


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
                    optional

            })


    return subjects


# ============================================================
# SUBJECT COMPLETE
#
# IMPORTANT:
#
# F হলেও Mark + Grade দুটোই required.
# ============================================================

def is_subject_complete(
    subject
):

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


    mark_valid = (

        mark is not None

        and

        str(mark).strip() != ""

    )


    grade_valid = bool(
        grade
    )


    # F-ও এখানে valid,
    # কিন্তু Mark ছাড়া valid নয়।

    return (
        mark_valid
        and
        grade_valid
    )


# ============================================================
# UNIQUE SUBJECT MAP
# ============================================================

def get_unique_subject_map(
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

        return {}


    subject_map = {}


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


        if not code:

            continue


        subject_map[code] = subject


    return subject_map


# ============================================================
# MISSING SUBJECTS
# ============================================================

def get_missing_subjects(
    student
):

    subject_map = (
        get_unique_subject_map(
            student
        )
    )


    missing = []


    # --------------------------------------------------------
    # 12 subjects না থাকলে incomplete
    # --------------------------------------------------------

    if len(subject_map) != EXPECTED_SUBJECT_COUNT:

        missing.append(
            f"subject_count:"
            f"{len(subject_map)}/"
            f"{EXPECTED_SUBJECT_COUNT}"
        )


    # --------------------------------------------------------
    # প্রতিটি subject-এর Mark + Grade check
    # --------------------------------------------------------

    for code, subject in subject_map.items():

        if not is_subject_complete(
            subject
        ):

            missing.append(
                code
            )


    # --------------------------------------------------------
    # Required code mode
    # --------------------------------------------------------

    if REQUIRED_SUBJECT_CODES:

        for code in REQUIRED_SUBJECT_CODES:

            if code not in subject_map:

                missing.append(
                    code
                )

            elif not is_subject_complete(
                subject_map[code]
            ):

                missing.append(
                    code
                )


    return sorted(
        set(missing)
    )


# ============================================================
# STUDENT COMPLETE
# ============================================================

def is_student_complete(
    student
):

    subject_map = (
        get_unique_subject_map(
            student
        )
    )


    # অবশ্যই 12টি unique subject
    if len(subject_map) != EXPECTED_SUBJECT_COUNT:

        return False


    # প্রত্যেক subject complete হতে হবে
    for subject in subject_map.values():

        if not is_subject_complete(
            subject
        ):

            return False


    # Required codes থাকলে সেগুলোও থাকতে হবে
    if REQUIRED_SUBJECT_CODES:

        if not REQUIRED_SUBJECT_CODES.issubset(
            set(subject_map.keys())
        ):

            return False


        for code in REQUIRED_SUBJECT_CODES:

            if not is_subject_complete(
                subject_map[code]
            ):

                return False


    return True


# ============================================================
# TOTAL SCORE
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

        grade = normalize_grade(
            subject.get(
                "grade",
                ""
            )
        )


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
            []

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

            ("Roll", "roll"),

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
    # VALID RESULT CHECK
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
    # CLEAN STRING FIELDS
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
# GENERATE ALL ROLLS
# ============================================================

def generate_all_rolls():

    rolls = []


    for group_name, (
        start,
        end
    ) in ROLL_RANGES.items():

        for roll in range(
            start,
            end + 1
        ):

            rolls.append(
                (
                    group_name,
                    roll
                )
            )


    return rolls


ALL_ROLLS = generate_all_rolls()


# ============================================================
# GROUP LOOKUP
# ============================================================

def get_group_for_roll(
    roll
):

    roll = int(roll)


    for group_name, (
        start,
        end
    ) in ROLL_RANGES.items():

        if start <= roll <= end:

            return group_name


    return ""


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
# SUPABASE LOAD
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
# BEFORE COUNTS
# ============================================================

total_supabase_before = len(
    supabase_students
)


incomplete_before = sum(

    1

    for student
    in supabase_students.values()

    if not is_student_complete(
        student
    )

)


complete_before = (
    total_supabase_before
    -
    incomplete_before
)


# ============================================================
# SEPARATE COMPLETE / INCOMPLETE
# ============================================================

incomplete_supabase = {}

complete_supabase = {}


for roll, student in (
    supabase_students.items()
):

    if is_student_complete(
        student
    ):

        complete_supabase[roll] = student

    else:

        incomplete_supabase[roll] = student


# ============================================================
# STATUS
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
    "SUPABASE DATA STATUS",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Total:",
    total_supabase_before,
    flush=True
)

print(
    "Complete 12/12:",
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
# INCOMPLETE EXAMPLES
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
# CURSOR
# ============================================================

cursor = load_cursor()


last_processed_roll = int(
    cursor.get(
        "last_processed_roll",
        0
    )
)


cycle = int(
    cursor.get(
        "cycle",
        1
    )
)


print(
    "",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "PERSISTENT COLLECTION CURSOR",
    flush=True
)

print(
    "=" * 70,
    flush=True
)

print(
    "Previous last processed roll:",
    last_processed_roll,
    flush=True
)

print(
    "Current cycle:",
    cycle,
    flush=True
)

print(
    "=" * 70,
    flush=True
)


# ============================================================
# BUILD TARGET ROLLS
#
# ONLY:
#
# 1. Roll নেই
# 2. Roll incomplete
#
# Complete roll কখনো target হবে না.
# ============================================================

target_rolls = []


for group_name, roll_number in ALL_ROLLS:

    roll = str(
        roll_number
    )


    if roll not in supabase_students:

        target_rolls.append(
            (
                group_name,
                roll
            )
        )

        continue


    existing = supabase_students[
        roll
    ]


    if not is_student_complete(
        existing
    ):

        target_rolls.append(
            (
                group_name,
                roll
            )
        )


# ============================================================
# SORT
# ============================================================

target_rolls.sort(
    key=lambda x: int(x[1])
)


# ============================================================
# TARGET COUNTS
# ============================================================

total_targets = len(
    target_rolls
)


new_target_count = sum(

    1

    for group, roll
    in target_rolls

    if roll not in supabase_students

)


repair_target_count = sum(

    1

    for group, roll
    in target_rolls

    if roll in supabase_students

)


# ============================================================
# SELECT NEXT BATCH
# ============================================================

run_targets = [

    item

    for item in target_rolls

    if int(item[1])
    >
    last_processed_roll

][
    :BATCH_SIZE
]


# ============================================================
# FULL CYCLE WRAP
# ============================================================

wrapped_cycle = False


if not run_targets and target_rolls:

    cycle += 1

    wrapped_cycle = True


    print(
        "",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    print(
        "FULL TARGET CYCLE COMPLETED",
        flush=True
    )

    print(
        "Starting new cycle...",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )


    run_targets = target_rolls[
        :BATCH_SIZE
    ]


# ============================================================
# TARGET INFO
# ============================================================

targets_after_cursor = sum(

    1

    for group, roll
    in target_rolls

    if int(roll)
    >
    last_processed_roll

)


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
    "Complete Supabase:",
    len(complete_supabase),
    flush=True
)

print(
    "Incomplete Supabase:",
    len(incomplete_supabase),
    flush=True
)

print(
    "New targets:",
    new_target_count,
    flush=True
)

print(
    "Repair targets:",
    repair_target_count,
    flush=True
)

print(
    "Total targets:",
    total_targets,
    flush=True
)

print(
    "Targets after cursor:",
    targets_after_cursor,
    flush=True
)

print(
    "This run:",
    len(run_targets),
    flush=True
)

print(
    "Previous cursor:",
    last_processed_roll,
    flush=True
)

if run_targets:

    print(
        "Batch first roll:",
        run_targets[0][1],
        flush=True
    )

    print(
        "Batch last roll:",
        run_targets[-1][1],
        flush=True
    )


print(
    "Cycle:",
    cycle,
    flush=True
)

print(
    "=" * 70,
    flush=True
)


# ============================================================
# NOTHING TO PROCESS
# ============================================================

if not run_targets:

    print(
        "",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    print(
        "NO TARGETS FOUND",
        flush=True
    )

    print(
        "All known students are complete.",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )


    save_cursor(
        last_processed_roll,
        cycle
    )


    raise SystemExit(0)


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

        allow_redirects=True

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

complete_skipped = 0


# ============================================================
# RUN DUPLICATE PROTECTION
# ============================================================

run_processed_rolls = set()


# ============================================================
# FAILED THIS RUN
# ============================================================

run_failed_rolls = []


# ============================================================
# SAVE CURSOR
# ============================================================

def update_cursor(
    roll,
    cycle
):

    global last_processed_roll

    try:

        save_cursor(
            int(roll),
            cycle
        )

        last_processed_roll = int(
            roll
        )

        return True

    except Exception as e:

        print(
            "Cursor save error:",
            e,
            flush=True
        )

        return False


# ============================================================
# UPDATE LOCAL STUDENT
# ============================================================

def update_local_student(
    student
):

    roll = str(
        student.get(
            "roll",
            ""
        )
    ).strip()


    if not roll:

        return


    local_students[roll] = student


    found = False


    for index, existing in enumerate(
        students
    ):

        if not isinstance(
            existing,
            dict
        ):

            continue


        if str(
            existing.get(
                "roll",
                ""
            )
        ).strip() == roll:

            students[index] = student

            found = True

            break


    if not found:

        students.append(
            student
        )


# ============================================================
# SUPABASE UPSERT
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
                )

        }


        response = (

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


        # Supabase response check
        if response is None:

            return (
                False,
                "Empty Supabase response"
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

    # --------------------------------------------------------
    # Duplicate protection
    # --------------------------------------------------------

    if roll in run_processed_rolls:

        print(
            "DUPLICATE PROTECTED:",
            roll,
            flush=True
        )

        continue


    run_processed_rolls.add(
        roll
    )


    processed += 1


    # ========================================================
    # CHECK CURRENT SUPABASE MEMORY
    # ========================================================

    old_student = (
        supabase_students.get(
            roll
        )
    )


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # যদি already complete হয়,
    # request করার দরকার নেই।
    # --------------------------------------------------------

    if old_student is not None:

        if is_student_complete(
            old_student
        ):

            complete_skipped += 1

            print(
                "",
                flush=True
            )

            print(
                f"[{processed}/{len(run_targets)}] "
                f"{group_name} | Roll: {roll}",
                flush=True
            )

            print(
                "✓ ALREADY COMPLETE 12/12",
                flush=True
            )

            print(
                "→ SKIP REQUEST",
                flush=True
            )

            update_cursor(
                int(roll),
                cycle
            )

            continue


    is_repair = (
        old_student is not None
    )


    # ========================================================
    # HEADER
    # ========================================================

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

        missing_old = (
            get_missing_subjects(
                old_student
            )
        )


        print(
            "MODE: FULL REPAIR",
            flush=True
        )

        print(
            "Old missing:",
            ", ".join(
                missing_old
            ),
            flush=True
        )

        print(
            "Old subjects will NOT be merged.",
            flush=True
        )

        print(
            "New 12-subject result will REPLACE old data.",
            flush=True
        )


    else:

        print(
            "MODE: NEW STUDENT",
            flush=True
        )


    # ========================================================
    # ATTEMPTED
    # ========================================================

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

                allow_redirects=True

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


        run_failed_rolls.append({
            "roll":
                roll,

            "group":
                group_name,

            "reason":
                "Temporary request failure",

            "timestamp":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })


        # Cursor move করবে যাতে batch আটকে না যায়.
        # পরবর্তী cycle-এ আবার target হবে।

        update_cursor(
            int(roll),
            cycle
        )


        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
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


        run_failed_rolls.append({

            "roll":
                roll,

            "group":
                group_name,

            "reason":
                f"Parsing error: {e}",

            "timestamp":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })


        update_cursor(
            int(roll),
            cycle
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

            "timestamp":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })


        failed_set.add(
            roll
        )


        run_failed_rolls.append({

            "roll":
                roll,

            "group":
                group_name,

            "reason":
                "No valid result",

            "timestamp":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })


        update_cursor(
            int(roll),
            cycle
        )


        continue


    # ========================================================
    # IMPORTANT:
    #
    # NO OLD SUBJECT MERGE
    #
    # New parsed result = new source of truth.
    # ========================================================

    parsed["subjects"] = parsed.get(
        "subjects",
        []
    )


    # ========================================================
    # BASIC INFO FALLBACK ONLY
    #
    # Subjects কখনো old data থেকে নেওয়া হবে না।
    # ========================================================

    if old_student:

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

                    str(
                        new_value
                    ).strip() == ""
                )

                and

                old_value not in (
                    None,
                    ""
                )

            ):

                parsed[key] = old_value


    # ========================================================
    # RECALCULATE TOTAL
    # ========================================================

    parsed["total_score"] = (
        calculate_total_score(
            parsed["subjects"]
        )
    )


    # ========================================================
    # PRINT RESULT
    # ========================================================

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
        "Subjects found:",
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

        complete_status = (
            "COMPLETE"
            if is_subject_complete(
                subject
            )
            else
            "INCOMPLETE"
        )


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
            "|",
            complete_status,
            flush=True
        )


    # ========================================================
    # CHECK COMPLETENESS
    # ========================================================

    missing = get_missing_subjects(
        parsed
    )


    # ========================================================
    # INCOMPLETE RESULT
    # ========================================================

    if missing:

        still_incomplete += 1


        print(
            "",
            flush=True
        )


        print(
            "⚠ NEW RESULT STILL INCOMPLETE",
            flush=True
        )


        print(
            "Missing:",
            ", ".join(
                missing
            ),
            flush=True
        )


        print(
            "Saving NEW partial result.",
            flush=True
        )


        # ----------------------------------------------------
        # IMPORTANT:
        #
        # পুরোনো incomplete data merge হবে না।
        # parsed পুরো নতুন result।
        # ----------------------------------------------------

        supabase_ok, message = (
            supabase_upsert_student(
                parsed
            )
        )


        if supabase_ok:

            supabase_saved += 1


            if is_repair:

                repaired += 1


                print(
                    "✓ OLD INCOMPLETE RECORD REPLACED",
                    flush=True
                )

            else:

                new_students += 1


                print(
                    "✓ NEW PARTIAL STUDENT SAVED",
                    flush=True
                )


            # Memory update
            supabase_students[roll] = parsed


            update_local_student(
                parsed
            )


        else:

            supabase_errors += 1


            print(
                "SUPABASE ERROR:",
                message,
                flush=True
            )


        # ----------------------------------------------------
        # Cursor
        # ----------------------------------------------------

        update_cursor(
            int(roll),
            cycle
        )


        # ----------------------------------------------------
        # Checkpoint
        # ----------------------------------------------------

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


        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )


        continue


    # ========================================================
    # COMPLETE RESULT
    # ========================================================

    print(
        "",
        flush=True
    )


    print(
        "✓ COMPLETE 12/12",
        flush=True
    )


    print(
        "All subjects have Mark + Grade.",
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


        # Later cycle-এ আবার target হবে।

        update_cursor(
            int(roll),
            cycle
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

    supabase_saved += 1

    successful += 1


    if is_repair:

        repaired += 1


        print(
            "✓ REPAIRED + REPLACED:",
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
    # MEMORY UPDATE
    # ========================================================

    supabase_students[roll] = parsed


    update_local_student(
        parsed
    )


    # ========================================================
    # CURSOR
    # ========================================================

    update_cursor(
        int(roll),
        cycle
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


        save_cursor(
            last_processed_roll,
            cycle
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
# FINAL CURSOR
# ============================================================

if run_targets:

    final_batch_last_roll = int(
        run_targets[-1][1]
    )


    save_cursor(
        final_batch_last_roll,
        cycle
    )


    last_processed_roll = (
        final_batch_last_roll
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
# REMAINING TARGETS
# ============================================================

remaining_targets = 0

remaining_new = 0

remaining_repairs = 0


for group_name, roll_number in ALL_ROLLS:

    roll = str(
        roll_number
    )


    if roll not in supabase_students:

        remaining_targets += 1

        remaining_new += 1

        continue


    student = supabase_students[
        roll
    ]


    if not is_student_complete(
        student
    ):

        remaining_targets += 1

        remaining_repairs += 1


# ============================================================
# FINAL COMPLETE COUNT
# ============================================================

final_complete_count = (
    final_supabase_count
    -
    remaining_incomplete
)


# ============================================================
# SUMMARY
# ============================================================

summary = {

    "year":
        YEAR,

    "board":
        BOARD,

    "expected_subject_count":
        EXPECTED_SUBJECT_COUNT,

    "total_supabase_before":
        total_supabase_before,

    "complete_before":
        complete_before,

    "incomplete_before":
        incomplete_before,

    "target_total":
        total_targets,

    "new_targets":
        new_target_count,

    "repair_targets":
        repair_target_count,

    "processed_this_run":
        processed,

    "complete_skipped_this_run":
        complete_skipped,

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

    "complete_after":
        final_complete_count,

    "remaining_incomplete":
        remaining_incomplete,

    "remaining_targets":
        remaining_targets,

    "remaining_new":
        remaining_new,

    "remaining_repairs":
        remaining_repairs,

    "batch_size":
        BATCH_SIZE,

    "required_subject_codes":
        sorted(
            REQUIRED_SUBJECT_CODES
        ),

    "auto_check_all_subjects":
        not bool(
            REQUIRED_SUBJECT_CODES
        ),

    "last_processed_roll":
        last_processed_roll,

    "cycle":
        cycle,

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
    "Expected subjects:",
    EXPECTED_SUBJECT_COUNT,
    flush=True
)

print(
    "Processed:",
    processed,
    flush=True
)

print(
    "Already complete skipped:",
    complete_skipped,
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
    "Complete after:",
    final_complete_count,
    flush=True
)

print(
    "Remaining incomplete:",
    remaining_incomplete,
    flush=True
)

print(
    "Remaining targets:",
    remaining_targets,
    flush=True
)

print(
    "Remaining new:",
    remaining_new,
    flush=True
)

print(
    "Remaining repairs:",
    remaining_repairs,
    flush=True
)

print(
    "Last processed roll:",
    last_processed_roll,
    flush=True
)

print(
    "Current cycle:",
    cycle,
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