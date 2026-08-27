import os
import json
import time
import random
import re
import hashlib
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

YEAR = 2026
BOARD = "Chattogram Board"

BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/"
)

INDIVIDUAL_URL = BASE_URL + "individual/"

SUPABASE_TABLE = os.getenv(
    "SUPABASE_TABLE",
    "students"
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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

CURSOR_FILE = os.path.join(
    OUTPUT_DIR,
    "new_collection_cursor.json"
)

REPAIR_CURSOR_FILE = os.path.join(
    OUTPUT_DIR,
    "repair_cursor.json"
)

REPAIR_SIGNATURE_FILE = os.path.join(
    OUTPUT_DIR,
    "repair_signatures.json"
)

BATCH_SIZE = 10000

SAVE_EVERY = 500

MIN_DELAY = 0.10
MAX_DELAY = 0.20

MAX_RETRIES = 3

REQUEST_TIMEOUT = (7, 20)

SUPABASE_PAGE_SIZE = 1000


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
# EXPECTED SUBJECT COUNT
# ============================================================

EXPECTED_SUBJECTS = 12


# ============================================================
# HEADERS
# ============================================================

HEADERS = {

    "User-Agent":
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36",

    "Accept":
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8",

    "Accept-Language":
        "en-US,en;q=0.9",

    "Connection":
        "keep-alive",
}


# ============================================================
# START
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

print("=" * 70)
print("SSC 2026 FULL SUBJECT-WISE COLLECTOR")
print("12 SUBJECT / F-GRADE SAFE / REPAIR VERSION")
print("=" * 70)

print("Expected subjects:", EXPECTED_SUBJECTS)
print("Batch size:", BATCH_SIZE)
print("Save every:", SAVE_EVERY)
print("Delay:", MIN_DELAY, "-", MAX_DELAY)
print("Max retries:", MAX_RETRIES)

print("")
print("RULES:")
print("")
print("12 subjects + valid Grade = COMPLETE -> SKIP")
print("F + Mark=None = VALID")
print("F + Mark = VALID")
print("Normal Grade + Mark = VALID")
print("Normal Grade + Mark=None = INCOMPLETE")
print("Missing Grade = INCOMPLETE")
print("Incomplete existing student = REPAIR")
print("Old incomplete subjects are NEVER merged")
print("New result completely replaces old result")
print("Repair queue = FIRST")
print("New queue = SECOND")
print("Already complete students = NEVER recollected")
print("Same repair result = NEVER recollected repeatedly")
print("=" * 70)


# ============================================================
# SUPABASE
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

print("Supabase: CONNECTED")
print("Supabase table:", SUPABASE_TABLE)


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# JSON HELPERS
# ============================================================

def save_json(path, data):

    temp = path + ".tmp"

    with open(
        temp,
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
        temp,
        path
    )


def load_json(path, default):

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
            "JSON load error:",
            path,
            e
        )

        return default


# ============================================================
# TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


# ============================================================
# GRADE
# ============================================================

VALID_GRADES = {
    "A+",
    "A",
    "A-",
    "B",
    "C",
    "D",
    "F"
}


def normalize_grade(value):

    value = clean_text(value)

    if not value:
        return ""

    value = (
        value
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
        .upper()
    )

    if value in VALID_GRADES:
        return value

    return ""


# ============================================================
# MARK
# ============================================================

def normalize_mark(value):

    if value is None:
        return None

    value = clean_text(value)

    if not value:
        return None

    if not re.fullmatch(
        r"\d{1,3}",
        value
    ):
        return None

    try:

        number = int(value)

    except Exception:

        return None

    if 0 <= number <= 300:
        return number

    return None


# ============================================================
# SUBJECT VALUE PARSER
# ============================================================

def parse_subject_values(values):

    mark = None
    grade = ""

    for raw in values:

        value = clean_text(raw)

        if not value:
            continue

        normalized = (
            value
            .replace(" ", "")
            .upper()
        )

        # ----------------------------------------------------
        # 184(A+)
        # ----------------------------------------------------

        match = re.fullmatch(
            r"(\d{1,3})"
            r"\("
            r"(A\+|A-|A|B|C|D|F)"
            r"\)",
            normalized
        )

        if match:

            return (
                int(match.group(1)),
                match.group(2)
            )

        # ----------------------------------------------------
        # 184A+
        # ----------------------------------------------------

        match = re.fullmatch(
            r"(\d{1,3})"
            r"(A\+|A-|A|B|C|D|F)",
            normalized
        )

        if match:

            return (
                int(match.group(1)),
                match.group(2)
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
            normalized
        )

        if match:

            grade = match.group(1)

            continue

        # ----------------------------------------------------
        # Mark only
        # ----------------------------------------------------

        parsed_mark = normalize_mark(
            normalized
        )

        if parsed_mark is not None:

            mark = parsed_mark

    return (
        mark,
        grade
    )


# ============================================================
# SUBJECT PARSER
# ============================================================

def parse_subjects(soup):

    subjects = []
    seen_codes = set()

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

            code = values[0].strip()

            if not re.fullmatch(
                r"\d{3,5}",
                code
            ):
                continue

            if code in seen_codes:
                continue

            subject_name = clean_text(
                values[1]
            )

            if not subject_name:
                continue

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

                "code": code,

                "subject": subject_name,

                "mark": mark,

                "grade": grade,

                "optional": optional,

            })

            seen_codes.add(code)

    return subjects


# ============================================================
# SUBJECT VALIDATION
# ============================================================
#
# IMPORTANT:
#
# F + None = VALID
#
# For normal grades:
# Mark + Grade required.
#
# For F:
# Grade F itself is enough.
#
# ============================================================

def subject_complete(subject):

    if not isinstance(
        subject,
        dict
    ):
        return False

    grade = normalize_grade(
        subject.get("grade")
    )

    mark = normalize_mark(
        subject.get("mark")
    )

    # No grade = incomplete
    if not grade:
        return False

    # ========================================================
    # F GRADE
    # ========================================================
    #
    # F + None is VALID.
    # F + Mark is also VALID.
    #
    if grade == "F":

        return True

    # ========================================================
    # NORMAL GRADE
    # ========================================================

    if mark is not None:

        return True

    return False


# ============================================================
# STUDENT COMPLETE
# ============================================================

def student_complete(student):

    if not isinstance(
        student,
        dict
    ):
        return False

    subjects = student.get(
        "subjects",
        []
    )

    if not isinstance(
        subjects,
        list
    ):
        return False

    # Exactly 12 subjects
    if len(subjects) != EXPECTED_SUBJECTS:
        return False

    codes = []

    for subject in subjects:

        if not subject_complete(
            subject
        ):
            return False

        code = str(
            subject.get(
                "code",
                ""
            )
        ).strip()

        if not code:
            return False

        codes.append(code)

    # Duplicate subject code invalid
    if len(
        set(codes)
    ) != EXPECTED_SUBJECTS:

        return False

    return True


# ============================================================
# SUBJECT COMPLETENESS SCORE
# ============================================================

def subject_quality_score(student):

    """
    Higher score = better result.

    F + None counts as complete.
    """

    if not isinstance(
        student,
        dict
    ):
        return 0

    subjects = student.get(
        "subjects",
        []
    )

    if not isinstance(
        subjects,
        list
    ):
        return 0

    score = 0

    for subject in subjects:

        if not isinstance(
            subject,
            dict
        ):
            continue

        grade = normalize_grade(
            subject.get("grade")
        )

        mark = normalize_mark(
            subject.get("mark")
        )

        if not grade:
            continue

        # F + None is valid
        if grade == "F":

            score += 1

            if mark is not None:
                score += 1

            continue

        # Normal grade + mark
        if mark is not None:

            score += 1

    return score


# ============================================================
# MISSING SUBJECTS
# ============================================================

def get_missing_subjects(student):

    if not isinstance(
        student,
        dict
    ):
        return ["invalid"]

    subjects = student.get(
        "subjects",
        []
    )

    if not isinstance(
        subjects,
        list
    ):
        return ["subjects"]

    missing = []

    for subject in subjects:

        if not isinstance(
            subject,
            dict
        ):
            missing.append(
                "invalid"
            )

            continue

        code = str(
            subject.get(
                "code",
                ""
            )
        ).strip()

        grade = normalize_grade(
            subject.get("grade")
        )

        mark = normalize_mark(
            subject.get("mark")
        )

        # No grade
        if not grade:

            missing.append(
                code or "unknown"
            )

            continue

        # F + None is NOT missing
        if grade == "F":

            continue

        # Normal grade but no mark
        if mark is None:

            missing.append(
                code or "unknown"
            )

    if len(subjects) != EXPECTED_SUBJECTS:

        missing.append(
            f"SUBJECT_COUNT="
            f"{len(subjects)}/{EXPECTED_SUBJECTS}"
        )

    return sorted(
        set(missing)
    )


# ============================================================
# GPA
# ============================================================

def find_gpa(soup):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    patterns = [

        r"\bGPA\s*[:=]\s*"
        r"([0-5](?:\.[0-9]+)?)",

        r"\bGPA\s+"
        r"([0-5](?:\.[0-9]+)?)",

        r"\bFINAL\s+RESULT\s*[:=]?\s*"
        r"([0-5](?:\.[0-9]+)?)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
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
# RESULT
# ============================================================

def find_result(
    soup,
    subjects
):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    ).upper()

    patterns = [

        r"\bRESULT\s*[:\-]\s*"
        r"(PASS|FAIL)",

        r"\bFINAL\s+RESULT\s*[:\-]?\s*"
        r"(PASS|FAIL)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            return match.group(1)

    for subject in subjects:

        if normalize_grade(
            subject.get(
                "grade"
            )
        ) == "F":

            return "FAIL"

    return ""


# ============================================================
# FIELD
# ============================================================

def field_after_label(
    values,
    labels
):

    labels = {
        x.lower()
        for x in labels
    }

    for index, value in enumerate(values):

        if value.lower() in labels:

            if index + 1 < len(values):

                return clean_text(
                    values[index + 1]
                )

    return ""


# ============================================================
# DISTRICT
# ============================================================

def district_from_institute(
    institute
):

    text = clean_text(
        institute
    ).upper()

    districts = {

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

    for key, value in districts.items():

        if key in text:

            return value

    return ""


# ============================================================
# PARSE RESULT
# ============================================================

def parse_result(
    html,
    roll,
    group
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    student = {

        "roll":
            str(roll),

        "name":
            "",

        "board":
            BOARD,

        "group":
            group,

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
    # BASIC INFO
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

        mappings = [

            (
                ["Roll No", "Roll"],
                "roll"
            ),

            (
                ["Name"],
                "name"
            ),

            (
                ["Board"],
                "board"
            ),

            (
                ["Group"],
                "group"
            ),

            (
                ["Father's Name", "Father Name"],
                "father_name"
            ),

            (
                ["Mother's Name", "Mother Name"],
                "mother_name"
            ),

            (
                ["Session"],
                "session"
            ),

            (
                ["Reg. NO", "Reg. No",
                 "Registration No"],
                "reg_no"
            ),

            (
                ["Type"],
                "type"
            ),

            (
                ["Institute"],
                "institute"
            ),

        ]

        for labels, key in mappings:

            value = field_after_label(
                values,
                labels
            )

            if value:

                student[key] = value

        result_value = field_after_label(
            values,
            ["Result"]
        )

        if result_value.upper() in (
            "PASS",
            "FAIL"
        ):

            student["result"] = (
                result_value.upper()
            )

    # ========================================================
    # SUBJECTS
    # ========================================================

    student["subjects"] = parse_subjects(
        soup
    )

    # ========================================================
    # GPA
    # ========================================================

    student["gpa"] = find_gpa(
        soup
    )

    # ========================================================
    # RESULT
    # ========================================================

    if not student["result"]:

        student["result"] = find_result(
            soup,
            student["subjects"]
        )

    # ========================================================
    # TOTAL SCORE
    # ========================================================

    total = 0
    has_mark = False

    for subject in student["subjects"]:

        mark = normalize_mark(
            subject.get("mark")
        )

        if mark is not None:

            total += mark
            has_mark = True

    if has_mark:

        student["total_score"] = total

    # ========================================================
    # DISTRICT
    # ========================================================

    student["district"] = (
        district_from_institute(
            student["institute"]
        )
    )

    # ========================================================
    # VALID PAGE
    # ========================================================

    has_identity = (
        bool(student["name"])
        or
        bool(student["institute"])
        or
        len(student["subjects"]) > 0
    )

    if not has_identity:

        return None

    return student


# ============================================================
# ALL ROLLS
# ============================================================

def generate_all_rolls():

    result = []

    for group, (
        start,
        end
    ) in ROLL_RANGES.items():

        for roll in range(
            start,
            end + 1
        ):

            result.append(
                (
                    group,
                    roll
                )
            )

    return result


ALL_ROLLS = generate_all_rolls()


# ============================================================
# SUPABASE LOAD
# ============================================================

def load_supabase_students():

    print("")
    print("Loading existing Supabase students...")

    result = {}

    offset = 0

    while True:

        try:

            response = (
                supabase
                .table(SUPABASE_TABLE)
                .select("*")
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
                e
            )

            raise SystemExit(
                "Could not load Supabase data."
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
            len(result)
        )

        if len(rows) < SUPABASE_PAGE_SIZE:

            break

        offset += SUPABASE_PAGE_SIZE

    print("")
    print(
        "Supabase total:",
        len(result)
    )

    return result


supabase_students = (
    load_supabase_students()
)


# ============================================================
# CLASSIFY
# ============================================================

complete_students = {}
incomplete_students = {}

for roll, student in (
    supabase_students.items()
):

    if student_complete(student):

        complete_students[roll] = student

    else:

        incomplete_students[roll] = student


print("")
print("=" * 70)
print("SUPABASE DATA STATUS")
print("=" * 70)

print(
    "Total:",
    len(supabase_students)
)

print(
    "Complete 12/12:",
    len(complete_students)
)

print(
    "Incomplete:",
    len(incomplete_students)
)

print("=" * 70)


# ============================================================
# CURSOR
# ============================================================

def load_number_cursor(path):

    data = load_json(
        path,
        {}
    )

    try:

        return int(
            data.get(
                "last_roll",
                0
            )
        )

    except Exception:

        return 0


def save_number_cursor(
    path,
    roll
):

    save_json(
        path,
        {

            "last_roll":
                int(roll),

            "updated_at":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        }
    )


new_cursor = load_number_cursor(
    CURSOR_FILE
)

repair_cursor = load_number_cursor(
    REPAIR_CURSOR_FILE
)


# ============================================================
# REPAIR SIGNATURES
# ============================================================

repair_signatures = load_json(
    REPAIR_SIGNATURE_FILE,
    {}
)

if not isinstance(
    repair_signatures,
    dict
):

    repair_signatures = {}


# ============================================================
# STUDENT SIGNATURE
# ============================================================

def student_signature(student):

    if not isinstance(
        student,
        dict
    ):
        return ""

    subjects = student.get(
        "subjects",
        []
    )

    normalized = []

    if isinstance(
        subjects,
        list
    ):

        for subject in subjects:

            if not isinstance(
                subject,
                dict
            ):
                continue

            normalized.append({

                "code":
                    str(
                        subject.get(
                            "code",
                            ""
                        )
                    ).strip(),

                "mark":
                    normalize_mark(
                        subject.get(
                            "mark"
                        )
                    ),

                "grade":
                    normalize_grade(
                        subject.get(
                            "grade"
                        )
                    ),

            })

    normalized.sort(
        key=lambda x: x["code"]
    )

    raw = json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# TARGET QUEUES
# ============================================================

repair_targets = []
new_targets = []


for group, roll_number in ALL_ROLLS:

    roll = str(roll_number)

    # --------------------------------------------------------
    # Existing complete = NEVER collect
    # --------------------------------------------------------

    if roll in complete_students:

        continue

    # --------------------------------------------------------
    # Existing incomplete = repair
    # --------------------------------------------------------

    if roll in incomplete_students:

        old_student = (
            incomplete_students[roll]
        )

        old_signature = (
            student_signature(
                old_student
            )
        )

        # If this exact incomplete data was already
        # attempted before, don't repeatedly request it.
        previous_signature = str(
            repair_signatures.get(
                roll,
                ""
            )
        )

        if (
            old_signature
            ==
            previous_signature
            and
            previous_signature
        ):

            continue

        repair_targets.append(
            (
                group,
                roll
            )
        )

    # --------------------------------------------------------
    # Completely absent = new
    # --------------------------------------------------------

    elif roll not in supabase_students:

        new_targets.append(
            (
                group,
                roll
            )
        )


repair_targets.sort(
    key=lambda x: int(x[1])
)

new_targets.sort(
    key=lambda x: int(x[1])
)


# ============================================================
# REPAIR CURSOR RESET
# ============================================================

repair_after_cursor = [

    item

    for item in repair_targets

    if int(item[1])
    >
    repair_cursor
]


if not repair_after_cursor:

    if repair_targets:

        print("")
        print(
            "Repair cursor reached available queue."
        )

        print(
            "Starting new repair cycle."
        )

        repair_cursor = 0

        save_number_cursor(
            REPAIR_CURSOR_FILE,
            0
        )

        repair_after_cursor = (
            repair_targets
        )


# ============================================================
# NEW QUEUE AFTER CURSOR
# ============================================================

new_after_cursor = [

    item

    for item in new_targets

    if int(item[1])
    >
    new_cursor
]


# ============================================================
# SELECT BATCH
# ============================================================

run_targets = []

repair_count = 0
new_count = 0


# ============================================================
# REPAIR FIRST
# ============================================================

for item in repair_after_cursor:

    if len(run_targets) >= BATCH_SIZE:

        break

    run_targets.append(item)

    repair_count += 1


# ============================================================
# NEW SECOND
# ============================================================

if len(run_targets) < BATCH_SIZE:

    remaining = (
        BATCH_SIZE -
        len(run_targets)
    )

    for item in new_after_cursor:

        if new_count >= remaining:

            break

        run_targets.append(item)

        new_count += 1


# ============================================================
# TARGET STATUS
# ============================================================

print("")
print("=" * 70)
print("COLLECTION TARGET")
print("=" * 70)

print(
    "Complete Supabase:",
    len(complete_students)
)

print(
    "Incomplete Supabase:",
    len(incomplete_students)
)

print(
    "Repair targets:",
    len(repair_targets)
)

print(
    "New targets:",
    len(new_targets)
)

print(
    "Repair cursor:",
    repair_cursor
)

print(
    "New cursor:",
    new_cursor
)

print(
    "Repair this run:",
    repair_count
)

print(
    "New this run:",
    new_count
)

print(
    "Total this run:",
    len(run_targets)
)

if run_targets:

    print(
        "Batch first roll:",
        run_targets[0][1]
    )

    print(
        "Batch last roll:",
        run_targets[-1][1]
    )

print("=" * 70)


if not run_targets:

    print("")
    print(
        "NO TARGETS FOUND."
    )

    print(
        "All available data is already collected "
        "or previously attempted."
    )

    raise SystemExit(0)


# ============================================================
# OPEN RESULT PAGE
# ============================================================

print("")
print(
    "Opening SSC result page..."
)

try:

    page = session.get(
        INDIVIDUAL_URL,
        headers={
            "Referer": BASE_URL
        },
        timeout=REQUEST_TIMEOUT
    )

    page.raise_for_status()

except Exception as e:

    raise SystemExit(
        f"Could not open result page: {e}"
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
# FORM
# ============================================================

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

form_url = urljoin(
    page.url,
    form_action
)


base_form_data = {}


for inp in form.find_all(
    "input"
):

    name = inp.get("name")

    if not name:

        continue

    input_type = inp.get(
        "type",
        "text"
    ).lower()

    if input_type in (
        "submit",
        "button",
        "reset",
        "image"
    ):

        continue

    if input_type in (
        "checkbox",
        "radio"
    ):

        if not inp.has_attr(
            "checked"
        ):

            continue

    base_form_data[name] = inp.get(
        "value",
        ""
    )


for select in form.find_all(
    "select"
):

    name = select.get("name")

    if not name:

        continue

    option = select.find(
        "option",
        selected=True
    )

    if not option:

        option = select.find(
            "option"
        )

    if option:

        base_form_data[name] = option.get(
            "value",
            option.get_text(
                strip=True
            )
        )


submit_fields = {}


for element in form.find_all(
    ["input", "button"]
):

    if element.get(
        "type",
        ""
    ).lower() == "submit":

        name = element.get(
            "name"
        )

        if name:

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
    "Form URL:",
    form_url
)

print(
    "Submit fields:",
    submit_fields
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
supabase_saved = 0
supabase_errors = 0
temporary_errors = 0
skipped_duplicate = 0

run_processed = set()


failed_rolls = load_json(
    FAILED_FILE,
    []
)

if not isinstance(
    failed_rolls,
    list
):

    failed_rolls = []


# ============================================================
# UPSERT
# ============================================================

def upsert_student(student):

    payload = {

        "roll":
            str(
                student.get(
                    "roll",
                    ""
                )
            ),

        "name":
            student.get(
                "name",
                ""
            ),

        "board":
            student.get(
                "board",
                BOARD
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

    try:

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

        return True, ""

    except Exception as e:

        return False, str(e)


# ============================================================
# LOCAL DATA
# ============================================================

students_local = load_json(
    STUDENTS_FILE,
    []
)

if not isinstance(
    students_local,
    list
):

    students_local = []


local_map = {}


for student in students_local:

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

        local_map[roll] = student


def update_local(student):

    roll = str(
        student.get(
            "roll",
            ""
        )
    ).strip()

    if roll:

        local_map[roll] = student


# ============================================================
# COLLECTION LOOP
# ============================================================

for group, roll in run_targets:

    if roll in run_processed:

        skipped_duplicate += 1

        continue

    run_processed.add(roll)

    processed += 1

    old_student = (
        supabase_students.get(
            roll
        )
    )

    is_repair = (
        old_student is not None
        and
        not student_complete(
            old_student
        )
    )

    print("")
    print("-" * 70)

    print(
        f"[{processed}/{len(run_targets)}]",
        group,
        "| Roll:",
        roll
    )

    if is_repair:

        print(
            "MODE: FULL REPAIR"
        )

        old_missing = (
            get_missing_subjects(
                old_student
            )
        )

        print(
            "Old missing:",
            ", ".join(old_missing)
        )

    else:

        print(
            "MODE: NEW STUDENT"
        )


    # ========================================================
    # REQUEST
    # ========================================================

    form_data = dict(
        base_form_data
    )

    form_data["roll"] = roll

    for key, value in submit_fields.items():

        form_data[key] = value


    response = None
    request_ok = False


    for attempt in range(
        MAX_RETRIES
    ):

        try:

            print(
                f"REQUEST: {roll} "
                f"attempt {attempt + 1}"
            )

            response = session.post(

                form_url,

                data=form_data,

                headers={
                    "Referer": page.url,
                    "Origin":
                        "https://sresult.bise-ctg.gov.bd",
                },

                timeout=REQUEST_TIMEOUT,

                allow_redirects=True,

            )

            print(
                "HTTP:",
                response.status_code
            )

            if response.status_code < 400:

                request_ok = True

                break

        except requests.exceptions.RequestException as e:

            temporary_errors += 1

            print(
                "REQUEST ERROR:",
                e
            )

        if attempt < MAX_RETRIES - 1:

            time.sleep(
                random.uniform(
                    1,
                    2
                )
            )


    # ========================================================
    # REQUEST FAILED
    # ========================================================

    if not request_ok:

        errors += 1

        failed_rolls.append({

            "roll":
                roll,

            "group":
                group,

            "reason":
                "request_failed",

            "timestamp":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })

        print(
            "REQUEST FAILED - will retry later."
        )

        continue


    # ========================================================
    # PARSE
    # ========================================================

    try:

        student = parse_result(
            response.text,
            roll,
            group
        )

    except Exception as e:

        errors += 1

        print(
            "PARSING ERROR:",
            e
        )

        continue


    # ========================================================
    # NOT FOUND
    # ========================================================

    if student is None:

        not_found += 1

        failed_rolls.append({

            "roll":
                roll,

            "group":
                group,

            "reason":
                "result_not_found",

            "timestamp":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })

        print(
            "NO VALID RESULT"
        )

        continue


    # ========================================================
    # RESULT INFO
    # ========================================================

    subjects = student.get(
        "subjects",
        []
    )

    print("")
    print(
        "FOUND:",
        student.get(
            "name",
            ""
        )
    )

    print(
        "Institute:",
        student.get(
            "institute",
            ""
        )
    )

    print(
        "GPA:",
        student.get(
            "gpa"
        )
    )

    print(
        "Total Score:",
        student.get(
            "total_score"
        )
    )

    print(
        "Subjects found:",
        len(subjects)
    )


    # ========================================================
    # PRINT SUBJECTS
    # ========================================================

    for subject in subjects:

        grade = normalize_grade(
            subject.get(
                "grade"
            )
        )

        mark = normalize_mark(
            subject.get(
                "mark"
            )
        )

        # ----------------------------------------------------
        # F + None = COMPLETE
        # ----------------------------------------------------

        if grade == "F":

            status = "COMPLETE / F VALID"

        elif grade and mark is not None:

            status = "COMPLETE"

        else:

            status = "INCOMPLETE"


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
            mark,
            "| Grade:",
            grade,
            "|",
            status
        )


    # ========================================================
    # NEW SIGNATURE
    # ========================================================

    new_signature = (
        student_signature(
            student
        )
    )

    new_quality = (
        subject_quality_score(
            student
        )
    )


    # ========================================================
    # COMPLETE CHECK
    # ========================================================

    complete = student_complete(
        student
    )


    # ========================================================
    # COMPLETE
    # ========================================================

    if complete:

        print("")
        print(
            "✓ COMPLETE 12/12"
        )

        print(
            "All 12 subjects are valid."
        )

        print(
            "F + Mark=None is accepted."
        )


        # ====================================================
        # SUPABASE UPSERT
        # ====================================================

        ok, message = upsert_student(
            student
        )

        if not ok:

            supabase_errors += 1

            print(
                "SUPABASE ERROR:",
                message
            )

            continue


        supabase_saved += 1
        successful += 1


        if is_repair:

            repaired += 1

            print(
                "✓ REPAIRED + REPLACED:",
                roll
            )

        else:

            new_students += 1

            print(
                "✓ NEW STUDENT SAVED:",
                roll
            )


        # ====================================================
        # MEMORY UPDATE
        # ====================================================

        supabase_students[roll] = (
            student
        )

        complete_students[roll] = (
            student
        )

        incomplete_students.pop(
            roll,
            None
        )

        update_local(
            student
        )


        # ====================================================
        # IMPORTANT:
        #
        # Remove repair signature.
        # Student is now complete.
        # ====================================================

        repair_signatures.pop(
            roll,
            None
        )


    # ========================================================
    # INCOMPLETE
    # ========================================================

    else:

        still_incomplete += 1

        missing = (
            get_missing_subjects(
                student
            )
        )

        print("")
        print(
            "⚠ STILL INCOMPLETE"
        )

        print(
            "Missing:",
            ", ".join(missing)
        )


        # ====================================================
        # NEW STUDENT INCOMPLETE
        #
        # Save whatever subjects were actually found.
        # ====================================================

        if not old_student:

            ok, message = upsert_student(
                student
            )

            if ok:

                supabase_saved += 1
                new_students += 1

                supabase_students[roll] = (
                    student
                )

                incomplete_students[roll] = (
                    student
                )

                update_local(
                    student
                )

                # Remember exact result
                repair_signatures[roll] = (
                    new_signature
                )

                print(
                    "✓ NEW STUDENT SAVED "
                    "WITH AVAILABLE SUBJECTS:",
                    roll
                )

            else:

                supabase_errors += 1

                print(
                    "SUPABASE ERROR:",
                    message
                )


        # ====================================================
        # EXISTING INCOMPLETE
        # ====================================================

        else:

            old_quality = (
                subject_quality_score(
                    old_student
                )
            )

            old_signature = (
                student_signature(
                    old_student
                )
            )


            print(
                "Old quality:",
                old_quality
            )

            print(
                "New quality:",
                new_quality
            )


            # ------------------------------------------------
            # If new data is better:
            # REPLACE old record.
            # ------------------------------------------------

            if new_quality > old_quality:

                ok, message = (
                    upsert_student(
                        student
                    )
                )

                if ok:

                    supabase_saved += 1
                    repaired += 1

                    supabase_students[roll] = (
                        student
                    )

                    incomplete_students[roll] = (
                        student
                    )

                    update_local(
                        student
                    )

                    repair_signatures[roll] = (
                        new_signature
                    )

                    print(
                        "✓ IMPROVED INCOMPLETE "
                        "RECORD REPLACED:",
                        roll
                    )

                else:

                    supabase_errors += 1

                    print(
                        "SUPABASE ERROR:",
                        message
                    )


            # ------------------------------------------------
            # Same quality but different data:
            #
            # If new record has more subjects, replace.
            # ------------------------------------------------

            elif (
                new_quality == old_quality
                and
                len(
                    student.get(
                        "subjects",
                        []
                    )
                )
                >
                len(
                    old_student.get(
                        "subjects",
                        []
                    )
                )
            ):

                ok, message = (
                    upsert_student(
                        student
                    )
                )

                if ok:

                    supabase_saved += 1
                    repaired += 1

                    supabase_students[roll] = (
                        student
                    )

                    incomplete_students[roll] = (
                        student
                    )

                    update_local(
                        student
                    )

                    repair_signatures[roll] = (
                        new_signature
                    )

                    print(
                        "✓ MORE SUBJECTS FOUND - "
                        "REPLACED:",
                        roll
                    )

                else:

                    supabase_errors += 1

                    print(
                        "SUPABASE ERROR:",
                        message
                    )


            # ------------------------------------------------
            # Exact same data
            # ------------------------------------------------

            elif new_signature == old_signature:

                repair_signatures[roll] = (
                    new_signature
                )

                print(
                    "↻ SAME DATA - NOT SAVED AGAIN."
                )

                print(
                    "This roll will not be "
                    "re-collected repeatedly."
                )


            # ------------------------------------------------
            # No improvement
            # ------------------------------------------------

            else:

                repair_signatures[roll] = (
                    new_signature
                )

                print(
                    "No improvement."
                )

                print(
                    "Old incomplete record kept."
                )

                print(
                    "New identical-quality "
                    "result will not be "
                    "re-collected repeatedly."
                )


    # ========================================================
    # CURSOR
    # ========================================================

    if is_repair:

        save_number_cursor(
            REPAIR_CURSOR_FILE,
            int(roll)
        )

        repair_cursor = int(roll)

    else:

        save_number_cursor(
            CURSOR_FILE,
            int(roll)
        )

        new_cursor = int(roll)


    # ========================================================
    # CHECKPOINT
    # ========================================================

    if processed % SAVE_EVERY == 0:

        print("")
        print(
            "Saving checkpoint..."
        )

        save_json(
            STUDENTS_FILE,
            list(
                local_map.values()
            )
        )

        save_json(
            FAILED_FILE,
            failed_rolls
        )

        save_json(
            REPAIR_SIGNATURE_FILE,
            repair_signatures
        )

        save_number_cursor(
            CURSOR_FILE,
            new_cursor
        )

        save_number_cursor(
            REPAIR_CURSOR_FILE,
            repair_cursor
        )

        print(
            "Checkpoint saved."
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

save_json(
    STUDENTS_FILE,
    list(
        local_map.values()
    )
)

save_json(
    FAILED_FILE,
    failed_rolls
)

save_json(
    REPAIR_SIGNATURE_FILE,
    repair_signatures
)


# ============================================================
# FINAL STATUS
# ============================================================

final_total = len(
    supabase_students
)


final_complete = sum(

    1

    for student
    in supabase_students.values()

    if student_complete(
        student
    )

)


final_incomplete = (
    final_total -
    final_complete
)


remaining_repair = 0
remaining_new = 0


for group, roll_number in ALL_ROLLS:

    roll = str(
        roll_number
    )

    if roll in supabase_students:

        if not student_complete(
            supabase_students[roll]
        ):

            remaining_repair += 1

    else:

        remaining_new += 1


# ============================================================
# SUMMARY
# ============================================================

summary = {

    "year":
        YEAR,

    "board":
        BOARD,

    "supabase_total":
        final_total,

    "complete_12_of_12":
        final_complete,

    "incomplete":
        final_incomplete,

    "processed_this_run":
        processed,

    "successful_complete":
        successful,

    "repaired":
        repaired,

    "new_students":
        new_students,

    "still_incomplete":
        still_incomplete,

    "not_found":
        not_found,

    "errors":
        errors,

    "temporary_request_errors":
        temporary_errors,

    "supabase_saved":
        supabase_saved,

    "supabase_errors":
        supabase_errors,

    "skipped_duplicate":
        skipped_duplicate,

    "remaining_repair":
        remaining_repair,

    "remaining_new":
        remaining_new,

    "remaining_total":
        (
            remaining_repair
            +
            remaining_new
        ),

    "repair_cursor":
        repair_cursor,

    "new_cursor":
        new_cursor,

    "batch_size":
        BATCH_SIZE,

    "rules":
        {

            "expected_subjects":
                EXPECTED_SUBJECTS,

            "f_grade_with_none_mark":
                "VALID",

            "f_grade_with_mark":
                "VALID",

            "normal_grade_requires_mark":
                True,

            "missing_grade":
                "INCOMPLETE",

            "complete_requires_12_subjects":
                True,

            "old_incomplete_merge":
                False,

            "full_record_replacement":
                True,

            "repair_first":
                True,

            "skip_existing_complete":
                True,

            "avoid_same_repair":
                True,

        },

    "roll_ranges":
        ROLL_RANGES,

}


save_json(
    SUMMARY_FILE,
    summary
)


# ============================================================
# FINAL OUTPUT
# ============================================================

print("")
print("=" * 70)
print("SSC COLLECTION COMPLETE")
print("=" * 70)

print(
    "Processed:",
    processed
)

print(
    "Successful complete:",
    successful
)

print(
    "Repaired:",
    repaired
)

print(
    "New students:",
    new_students
)

print(
    "Still incomplete:",
    still_incomplete
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

print("")
print(
    "Supabase total:",
    final_total
)

print(
    "Complete 12/12:",
    final_complete
)

print(
    "Incomplete:",
    final_incomplete
)

print(
    "Remaining repair:",
    remaining_repair
)

print(
    "Remaining new:",
    remaining_new
)

print(
    "Remaining total:",
    (
        remaining_repair
        +
        remaining_new
    )
)

print(
    "Repair cursor:",
    repair_cursor
)

print(
    "New cursor:",
    new_cursor
)

print("=" * 70)
print("DONE")
print("=" * 70)