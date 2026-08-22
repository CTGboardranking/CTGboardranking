import json
import os
import time
import re
import requests
from bs4 import BeautifulSoup

# ============================================================
# SETTINGS
# ============================================================

INPUT_FILE = "institution-collector/institutions.json"
OUTPUT_FILE = "institution-collector/student_results.json"

REQUEST_DELAY = 0.3
TEST_LIMIT = 1

BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/resultm.php"

TIMEOUT = 30

# ============================================================
# START
# ============================================================

print("=" * 70, flush=True)
print("SSC 2026 STUDENT RESULT COLLECTOR", flush=True)
print("=" * 70, flush=True)

# ============================================================
# LOAD INSTITUTIONS
# ============================================================

print(f"Loading: {INPUT_FILE}", flush=True)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    institutions = json.load(f)

if not isinstance(institutions, list):
    raise ValueError("institutions.json must contain a JSON array")

print(f"Raw records: {len(institutions)}", flush=True)

# ------------------------------------------------------------
# Remove metadata/header records
# ------------------------------------------------------------

valid_institutions = []

for item in institutions:

    if not isinstance(item, dict):
        continue

    eiin = str(item.get("eiin", "")).strip()

    # metadata/header object skip
    if not eiin:
        continue

    if eiin.lower() in {
        "metadata",
        "meta",
        "eiin_code",
        "eiin"
    }:
        continue

    # EIIN should normally be numeric
    if not eiin.isdigit():
        print(
            f"SKIP invalid EIIN: {eiin}",
            flush=True
        )
        continue

    valid_institutions.append(item)

institutions = valid_institutions

total = len(institutions)

print(
    f"Valid institutions: {total}",
    flush=True
)

print(
    f"TEST LIMIT: {TEST_LIMIT}",
    flush=True
)

# ============================================================
# LOAD PREVIOUS STUDENT RESULTS
# ============================================================

results = []

if os.path.exists(OUTPUT_FILE):

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            old_results = json.load(f)

        if isinstance(old_results, list):

            results = old_results

        print("=" * 70, flush=True)
        print("RESUME MODE", flush=True)
        print(
            f"Previously collected student records: {len(results)}",
            flush=True
        )
        print("=" * 70, flush=True)

    except Exception as e:

        print(
            "Could not load previous student result file.",
            flush=True
        )

        print(
            "Starting from empty result list.",
            flush=True
        )

        print(
            "Error:",
            e,
            flush=True
        )

# ============================================================
# EXISTING STUDENT KEYS
# ============================================================

existing_keys = set()

for item in results:

    if not isinstance(item, dict):
        continue

    eiin = str(
        item.get("eiin", "")
    ).strip()

    roll = str(
        item.get("roll", "")
    ).strip()

    if eiin and roll:

        existing_keys.add(
            f"{eiin}:{roll}"
        )

print(
    f"Existing EIIN+Roll records: {len(existing_keys)}",
    flush=True
)

# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update({

    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36",

    "Accept":
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8",

    "Accept-Language":
        "en-US,en;q=0.9",

    "Connection":
        "keep-alive"

})

# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def normalize_key(value):

    value = clean_text(value)

    value = value.lower()

    value = value.replace(
        ":",
        ""
    )

    value = value.replace(
        "-",
        " "
    )

    value = value.replace(
        "_",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def safe_number(value):

    value = clean_text(value)

    value = value.replace(
        ",",
        ""
    )

    value = value.replace(
        "%",
        ""
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    number = float(
        match.group(0)
    )

    if number.is_integer():
        return int(number)

    return number


def get_institution_name(institution):

    for key in [
        "institution_name",
        "institutionName",
        "name",
        "college_name",
        "collegeName",
        "school_name",
        "schoolName"
    ]:

        value = institution.get(
            key,
            ""
        )

        if clean_text(value):

            return clean_text(value)

    return ""


def get_district(institution):

    for key in [
        "district",
        "District",
        "district_name",
        "districtName"
    ]:

        value = institution.get(
            key,
            ""
        )

        if clean_text(value):

            return clean_text(value)

    return "Chattogram"


# ============================================================
# LABEL DETECTION
# ============================================================

def find_value_by_labels(soup, labels):

    wanted = [
        normalize_key(x)
        for x in labels
    ]

    # --------------------------------------------------------
    # TABLE CELLS
    # --------------------------------------------------------

    for row in soup.find_all("tr"):

        cells = row.find_all(
            ["td", "th"]
        )

        if len(cells) < 2:
            continue

        values = [
            clean_text(
                cell.get_text(
                    " ",
                    strip=True
                )
            )
            for cell in cells
        ]

        normalized = [
            normalize_key(x)
            for x in values
        ]

        for i, key in enumerate(normalized):

            for label in wanted:

                if (
                    key == label
                    or label in key
                ):

                    if i + 1 < len(values):

                        value = values[i + 1]

                        if value:

                            return value

    # --------------------------------------------------------
    # TEXT / DIV / SPAN
    # --------------------------------------------------------

    for element in soup.find_all(
        ["td", "th", "div", "span", "p", "li"]
    ):

        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        normalized = normalize_key(
            text
        )

        for label in wanted:

            pattern = (
                r"^"
                + re.escape(label)
                + r"\s*[:\-]?\s*(.+)$"
            )

            match = re.search(
                pattern,
                normalized,
                re.IGNORECASE
            )

            if match:

                return clean_text(
                    match.group(1)
                )

    return ""


# ============================================================
# ROLL
# ============================================================

def find_roll(soup):

    value = find_value_by_labels(
        soup,
        [
            "roll",
            "roll no",
            "roll no.",
            "roll number",
            "student roll"
        ]
    )

    if value:

        match = re.search(
            r"\b\d{4,10}\b",
            value
        )

        if match:

            return match.group(0)

    # fallback whole page
    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    patterns = [

        r"ROLL\s*(?:NO|NUMBER)?\s*[:\-]?\s*(\d{4,10})",

        r"ROLL\s*[:\-]\s*(\d{4,10})"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

    return ""


# ============================================================
# GPA
# ============================================================

def find_gpa(soup):

    value = find_value_by_labels(
        soup,
        [
            "gpa",
            "gpa final",
            "final gpa",
            "grade point average"
        ]
    )

    if value:

        match = re.search(
            r"\b[0-5](?:\.\d+)?\b",
            value
        )

        if match:

            return float(
                match.group(0)
            )

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    patterns = [

        r"GPA\s*[:\-]?\s*([0-5](?:\.\d+)?)",

        r"FINAL\s+GPA\s*[:\-]?\s*([0-5](?:\.\d+)?)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return float(
                match.group(1)
            )

    return None


# ============================================================
# RESULT STATUS
# ============================================================

def find_result_status(soup):

    value = find_value_by_labels(
        soup,
        [
            "result",
            "status"
        ]
    )

    if value:

        value_upper = value.upper()

        if "PASS" in value_upper:

            return "PASS"

        if "FAIL" in value_upper:

            return "FAIL"

        return value

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    if re.search(
        r"\bPASS\b",
        text,
        re.IGNORECASE
    ):

        return "PASS"

    if re.search(
        r"\bFAIL\b",
        text,
        re.IGNORECASE
    ):

        return "FAIL"

    return ""


# ============================================================
# SUBJECT PARSER
# ============================================================

def parse_subjects(soup):

    subjects = {}

    tables = soup.find_all(
        "table"
    )

    for table in tables:

        rows = table.find_all(
            "tr"
        )

        for row in rows:

            cells = row.find_all(
                ["td", "th"]
            )

            if len(cells) < 2:
                continue

            values = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )
                for cell in cells
            ]

            # remove empty cells
            values = [
                x for x in values
                if x
            ]

            if len(values) < 2:
                continue

            # ------------------------------------------------
            # Header detection
            # ------------------------------------------------

            joined = " ".join(
                normalize_key(x)
                for x in values
            )

            if (
                "subject" in joined
                and (
                    "mark" in joined
                    or "grade" in joined
                )
            ):

                continue

            # ------------------------------------------------
            # Try to identify subject row
            # ------------------------------------------------

            subject = values[0]

            if not subject:
                continue

            subject_normalized = normalize_key(
                subject
            )

            # Ignore summary rows
            ignored = [

                "total",
                "grand total",
                "gpa",
                "result",
                "status",
                "pass",
                "percentage",
                "percent",
                "app",
                "passed"

            ]

            if any(
                x == subject_normalized
                or x in subject_normalized
                for x in ignored
            ):

                continue

            marks = None
            grade = ""

            # ------------------------------------------------
            # Find numeric marks
            # ------------------------------------------------

            for value in values[1:]:

                number = safe_number(
                    value
                )

                if (
                    number is not None
                    and 0 <= number <= 200
                ):

                    # Avoid GPA-like values
                    if number > 5:

                        marks = number
                        break

            # ------------------------------------------------
            # Find grade
            # ------------------------------------------------

            for value in values[1:]:

                upper = value.upper()

                if upper in [
                    "A+",
                    "A",
                    "A-",
                    "B",
                    "C",
                    "D",
                    "F"
                ]:

                    grade = upper
                    break

            # ------------------------------------------------
            # Save
            # ------------------------------------------------

            if (
                marks is not None
                or grade
            ):

                subjects[subject] = {

                    "marks": marks,

                    "grade": grade

                }

    return subjects


# ============================================================
# PARSE COMPLETE STUDENT RESULT
# ============================================================

def parse_student_result(
    html,
    institution
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    roll = find_roll(
        soup
    )

    gpa = find_gpa(
        soup
    )

    result_status = find_result_status(
        soup
    )

    subjects = parse_subjects(
        soup
    )

    return {

        "eiin": str(
            institution.get(
                "eiin",
                ""
            )
        ).strip(),

        "institution_name":
            get_institution_name(
                institution
            ),

        "district":
            get_district(
                institution
            ),

        "roll": roll,

        "gpa": gpa,

        "result": result_status,

        "subjects": subjects

    }


# ============================================================
# SAVE
# ============================================================

def save_results():

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# COLLECTION
# ============================================================

limit = min(
    TEST_LIMIT,
    total
)

print("=" * 70, flush=True)
print("STARTING STUDENT COLLECTION", flush=True)
print(
    f"Target institutions: {limit}",
    flush=True
)
print("=" * 70, flush=True)

for index in range(limit):

    institution = institutions[index]

    eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()

    name = get_institution_name(
        institution
    )

    print("-" * 70, flush=True)

    print(
        f"[{index + 1}/{limit}]",
        flush=True
    )

    print(
        f"EIIN: {eiin}",
        flush=True
    )

    print(
        f"Institution: {name}",
        flush=True
    )

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    try:

        response = session.post(
            BASE_URL,
            data={
                "eiin": eiin
            },
            timeout=TIMEOUT
        )

        print(
            f"HTTP: {response.status_code}",
            flush=True
        )

        if response.status_code != 200:

            print(
                "ERROR: HTTP status is not 200",
                flush=True
            )

            time.sleep(
                REQUEST_DELAY
            )

            continue

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        parsed = parse_student_result(
            response.text,
            institution
        )

        roll = parsed.get(
            "roll",
            ""
        )

        gpa = parsed.get(
            "gpa"
        )

        result_status = parsed.get(
            "result",
            ""
        )

        subjects = parsed.get(
            "subjects",
            {}
        )

        # ----------------------------------------------------
        # IMPORTANT
        # ----------------------------------------------------

        # If this page is an institution summary
        # rather than an individual student result,
        # it may not contain a roll.
        #
        # We DO NOT save such a record as a student.

        if not roll:

            print(
                "NO STUDENT ROLL FOUND",
                flush=True
            )

            print(
                "This page may be institution summary data.",
                flush=True
            )

            time.sleep(
                REQUEST_DELAY
            )

            continue

        key = (
            f"{eiin}:{roll}"
        )

        if key in existing_keys:

            print(
                f"SKIP existing student: {roll}",
                flush=True
            )

            time.sleep(
                REQUEST_DELAY
            )

            continue

        # ----------------------------------------------------
        # SHOW
        # ----------------------------------------------------

        print(
            f"ROLL: {roll}",
            flush=True
        )

        print(
            f"GPA: {gpa}",
            flush=True
        )

        print(
            f"RESULT: {result_status}",
            flush=True
        )

        print(
            f"SUBJECTS FOUND: {len(subjects)}",
            flush=True
        )

        for subject, data in subjects.items():

            print(
                f"  {subject}: "
                f"{data.get('marks')} "
                f"/ {data.get('grade')}",
                flush=True
            )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        results.append(
            parsed
        )

        existing_keys.add(
            key
        )

        save_results()

        print(
            f"SAVED: {len(results)} student records",
            flush=True
        )

    except requests.exceptions.Timeout:

        print(
            "ERROR: Request timeout",
            flush=True
        )

    except requests.exceptions.RequestException as e:

        print(
            f"ERROR: Request failed - {e}",
            flush=True
        )

    except Exception as e:

        print(
            f"ERROR: {e}",
            flush=True
        )

    time.sleep(
        REQUEST_DELAY
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("=" * 70, flush=True)
print("STUDENT COLLECTION COMPLETED", flush=True)
print("=" * 70, flush=True)

print(
    f"Student records: {len(results)}",
    flush=True
)

print(
    f"Output: {OUTPUT_FILE}",
    flush=True
)

print("=" * 70, flush=True)