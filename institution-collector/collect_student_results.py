import json
import os
import time
import re
import requests
from bs4 import BeautifulSoup


# ============================================================
# SSC 2026 STUDENT RESULT COLLECTOR
# Chattogram Board
# ============================================================

INPUT_FILE = "institution-collector/institutions.json"
OUTPUT_FILE = "institution-collector/student_results.json"

REQUEST_DELAY = 0.3

# ------------------------------------------------------------
# TEST
# 1 = প্রথম institution
# 5 = প্রথম ৫টি institution
# None = সব institution
# ------------------------------------------------------------

TEST_LIMIT = 1286

BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/resultm.php"
)

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

print(
    f"Loading: {INPUT_FILE}",
    flush=True
)

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    raw_data = json.load(f)


# ------------------------------------------------------------
# institutions.json format:
#
# {
#   "metadata": {...},
#   "institutions": [...]
# }
#
# অথবা সরাসরি [...]
# ------------------------------------------------------------

if isinstance(raw_data, dict):

    institutions = raw_data.get(
        "institutions",
        []
    )

elif isinstance(raw_data, list):

    institutions = raw_data

else:

    raise ValueError(
        "Invalid institutions.json format"
    )


if not isinstance(
    institutions,
    list
):

    raise ValueError(
        "'institutions' must be a JSON array"
    )


print(
    f"Raw institutions: {len(institutions)}",
    flush=True
)


# ============================================================
# VALID INSTITUTIONS
# ============================================================

valid_institutions = []

for item in institutions:

    if not isinstance(
        item,
        dict
    ):
        continue

    eiin = str(
        item.get(
            "eiin",
            ""
        )
    ).strip()

    if not eiin:
        continue

    if not eiin.isdigit():
        continue

    valid_institutions.append(
        item
    )


institutions = valid_institutions

total_institutions = len(
    institutions
)


print(
    f"Valid institutions: {total_institutions}",
    flush=True
)

print(
    f"TEST LIMIT: {TEST_LIMIT}",
    flush=True
)


# ============================================================
# LOAD EXISTING RESULTS
# ============================================================

results = []

if os.path.exists(
    OUTPUT_FILE
):

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            old_data = json.load(f)


        if isinstance(
            old_data,
            list
        ):

            results = old_data


        print("=" * 70, flush=True)

        print(
            f"Previously collected: {len(results)}",
            flush=True
        )

        print("=" * 70, flush=True)


    except Exception as e:

        print(
            "Could not read previous student_results.json",
            flush=True
        )

        print(
            f"Error: {e}",
            flush=True
        )

        results = []


# ============================================================
# EXISTING EIIN + ROLL
# ============================================================

existing_keys = set()

for item in results:

    if not isinstance(
        item,
        dict
    ):
        continue

    eiin = str(
        item.get(
            "eiin",
            ""
        )
    ).strip()

    roll = str(
        item.get(
            "roll",
            ""
        )
    ).strip()

    if eiin and roll:

        existing_keys.add(
            f"{eiin}:{roll}"
        )


print(
    f"Existing EIIN+Roll records: "
    f"{len(existing_keys)}",
    flush=True
)


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update({

    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36",

    "Accept":
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,"
        "*/*;q=0.8",

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


def get_institution_name(
    institution
):

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

        value = clean_text(
            value
        )

        if value:
            return value

    return ""


def get_district(
    institution
):

    for key in [
        "district",
        "District",
        "district_name",
        "districtName"
    ]:

        value = clean_text(
            institution.get(
                key,
                ""
            )
        )

        if value:
            return value

    return "Chattogram"


def save_results():

    temp_file = (
        OUTPUT_FILE +
        ".tmp"
    )

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        OUTPUT_FILE
    )


# ============================================================
# SUBJECT CODE
# ============================================================

def normalize_subject_code(
    code
):

    return str(
        code
    ).strip()


# ============================================================
# PARSE SUBJECT RESULT
#
# Example:
#
# 101:T:172(A+)
#
# 107:T:170(A+)
#
# ============================================================

def parse_subject_string(
    subject_text
):

    subjects = {}

    if not subject_text:
        return subjects


    # --------------------------------------------------------
    # Example:
    #
    # 101:T:172(A+)
    # --------------------------------------------------------

    pattern = re.compile(
        r"(\d{3})"
        r"\s*:\s*"
        r"([A-Za-z]+)"
        r"\s*:\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"\(\s*"
        r"([A-Za-z+\\-]+)"
        r"\s*\)"
    )


    matches = pattern.findall(
        subject_text
    )


    for match in matches:

        code = match[0]

        result_type = match[1]

        marks_text = match[2]

        grade = match[3].upper()


        try:

            marks = float(
                marks_text
            )

            if marks.is_integer():

                marks = int(
                    marks
                )

        except Exception:

            marks = None


        subjects[
            normalize_subject_code(
                code
            )
        ] = {

            "marks": marks,

            "grade": grade,

            "type": result_type

        }


    return subjects


# ============================================================
# STUDENT LINE PARSER
#
# Example:
#
# 120629[5.00]:101:T:172(A+),107:T:170(A+),...
#
# ============================================================

def parse_student_line(
    line,
    institution,
    group
):

    line = clean_text(
        line
    )

    if not line:
        return None


    # --------------------------------------------------------
    # Student result format
    #
    # ROLL[GPA]:subject...
    #
    # --------------------------------------------------------

    pattern = re.compile(
        r"^"
        r"(\d{4,8})"
        r"\s*"
        r"\["
        r"([0-5](?:\.\d+)?)"
        r"\]"
        r"\s*:"
        r"(.*)"
        r"$"
    )


    match = pattern.match(
        line
    )


    if not match:

        return None


    roll = match.group(
        1
    ).strip()


    gpa_text = match.group(
        2
    ).strip()


    subject_text = match.group(
        3
    ).strip()


    # --------------------------------------------------------
    # Prevent EIIN being interpreted as roll
    #
    # EIIN 103086 etc.
    # --------------------------------------------------------

    institution_eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()


    if roll == institution_eiin:

        return None


    try:

        gpa = float(
            gpa_text
        )

    except Exception:

        gpa = None


    subjects = parse_subject_string(
        subject_text
    )


    return {

        "eiin":
            institution_eiin,

        "institution_name":
            get_institution_name(
                institution
            ),

        "district":
            get_district(
                institution
            ),

        "group":
            group,

        "roll":
            roll,

        "gpa":
            gpa,

        "result":
            "PASS",

        "subjects":
            subjects

    }


# ============================================================
# FIND RESULT TEXT
# ============================================================

def get_page_text(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    # --------------------------------------------------------
    # get_text() gives us the actual visible result text
    # --------------------------------------------------------

    text = soup.get_text(
        "\n",
        strip=True
    )


    return text


# ============================================================
# NORMALIZE RESULT TEXT
# ============================================================

def normalize_result_text(
    text
):

    lines = []

    for line in text.splitlines():

        line = clean_text(
            line
        )

        if line:

            lines.append(
                line
            )


    return lines


# ============================================================
# DETECT GROUP
# ============================================================

def detect_group(
    line,
    current_group
):

    upper = line.upper()


    if "SCIENCE" in upper:

        return "Science"


    if (
        "BUSINESS STUDIES" in upper
        or "BUSINESS" in upper
        or "COMMERCE" in upper
    ):

        return "Business Studies"


    if (
        "HUMANITIES" in upper
        or "ARTS" in upper
    ):

        return "Humanities"


    return current_group


# ============================================================
# FAILED STUDENT
#
# Examples:
#
# 319962[F1]
# 319965[FAIL]
# 319971[F2]
#
# ============================================================

def parse_failed_line(
    line,
    institution,
    group
):

    line = clean_text(
        line
    )


    pattern = re.compile(
        r"^"
        r"(\d{4,8})"
        r"\s*"
        r"\["
        r"([^\]]+)"
        r"\]"
        r"$"
    )


    match = pattern.match(
        line
    )


    if not match:

        return None


    roll = match.group(
        1
    ).strip()


    status = match.group(
        2
    ).strip().upper()


    institution_eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()


    if roll == institution_eiin:

        return None


    return {

        "eiin":
            institution_eiin,

        "institution_name":
            get_institution_name(
                institution
            ),

        "district":
            get_district(
                institution
            ),

        "group":
            group,

        "roll":
            roll,

        "gpa":
            None,

        "result":
            status,

        "subjects":
            {}

    }


# ============================================================
# PARSE COMPLETE INSTITUTION PAGE
# ============================================================

def parse_institution_results(
    html,
    institution
):

    text = get_page_text(
        html
    )


    lines = normalize_result_text(
        text
    )


    students = []

    current_group = ""


    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    in_success_section = False

    in_failed_section = False


    for line in lines:

        upper = line.upper()


        # ====================================================
        # GROUP DETECTION
        # ====================================================

        detected_group = detect_group(
            line,
            current_group
        )


        if detected_group != current_group:

            current_group = detected_group


        # ====================================================
        # SUCCESS SECTION
        # ====================================================

        if (
            "EXAMINEES SECURING" in upper
            or "ALL RESULTS" in upper
        ):

            in_success_section = True

            in_failed_section = False

            continue


        # ====================================================
        # FAILED SECTION
        # ====================================================

        if (
            "UNSUCCESSFUL" in upper
            or "OTHERS" in upper
        ):

            in_failed_section = True

            in_success_section = False

            continue


        # ====================================================
        # END
        # ====================================================

        if "END" in upper:

            break


        # ====================================================
        # SUCCESS STUDENT
        # ====================================================

        if in_success_section:

            student = parse_student_line(
                line,
                institution,
                current_group
            )


            if student:

                students.append(
                    student
                )

                continue


        # ====================================================
        # FAILED STUDENT
        # ====================================================

        if in_failed_section:

            student = parse_failed_line(
                line,
                institution,
                current_group
            )


            if student:

                students.append(
                    student
                )


    return students


# ============================================================
# DEBUG PRINT
# ============================================================

def print_student_sample(
    students,
    limit=5
):

    print(
        "-" * 70,
        flush=True
    )

    print(
        "SAMPLE STUDENTS",
        flush=True
    )


    for student in students[:limit]:

        print(
            f"ROLL: {student.get('roll')}",
            flush=True
        )

        print(
            f"GROUP: {student.get('group')}",
            flush=True
        )

        print(
            f"GPA: {student.get('gpa')}",
            flush=True
        )

        print(
            f"RESULT: {student.get('result')}",
            flush=True
        )

        print(
            f"SUBJECTS: "
            f"{len(student.get('subjects', {}))}",
            flush=True
        )


        subjects = student.get(
            "subjects",
            {}
        )


        for code, data in list(
            subjects.items()
        )[:5]:

            print(
                f"  {code}: "
                f"{data.get('marks')} "
                f"({data.get('grade')})",
                flush=True
            )


        print(
            "-" * 30,
            flush=True
        )


# ============================================================
# COLLECTION
# ============================================================

if TEST_LIMIT is None:

    target_institutions = institutions

else:

    target_institutions = institutions[
        :TEST_LIMIT
    ]


print("=" * 70, flush=True)

print(
    "STARTING STUDENT COLLECTION",
    flush=True
)

print(
    f"Target institutions: "
    f"{len(target_institutions)}",
    flush=True
)

print("=" * 70, flush=True)


# ============================================================
# MAIN LOOP
# ============================================================

for index, institution in enumerate(
    target_institutions,
    start=1
):

    eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()


    institution_name = get_institution_name(
        institution
    )


    print(
        "-" * 70,
        flush=True
    )


    print(
        f"[{index}/{len(target_institutions)}]",
        flush=True
    )


    print(
        f"EIIN: {eiin}",
        flush=True
    )


    print(
        f"Institution: {institution_name}",
        flush=True
    )


    # ========================================================
    # REQUEST
    # ========================================================

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


        html = response.text


        # ====================================================
        # PARSE
        # ====================================================

        students = parse_institution_results(
            html,
            institution
        )


        print(
            f"STUDENTS DETECTED: "
            f"{len(students)}",
            flush=True
        )


        if students:

            print_student_sample(
                students,
                limit=5
            )


        # ====================================================
        # SAVE STUDENTS
        # ====================================================

        new_count = 0


        for student in students:

            roll = str(
                student.get(
                    "roll",
                    ""
                )
            ).strip()


            if not roll:

                continue


            key = (
                f"{eiin}:{roll}"
            )


            if key in existing_keys:

                continue


            results.append(
                student
            )


            existing_keys.add(
                key
            )


            new_count += 1


        save_results()


        print(
            f"NEW STUDENTS SAVED: "
            f"{new_count}",
            flush=True
        )


        print(
            f"TOTAL STUDENT RECORDS: "
            f"{len(results)}",
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
# FINAL
# ============================================================

print("=" * 70, flush=True)

print(
    "STUDENT COLLECTION COMPLETED",
    flush=True
)

print("=" * 70, flush=True)


print(
    f"Student records: {len(results)}",
    flush=True
)


print(
    f"Output: {OUTPUT_FILE}",
    flush=True
)


# ============================================================
# FINAL SAMPLE
# ============================================================

if results:

    print(
        "=" * 70,
        flush=True
    )

    print(
        "FIRST SAVED RECORD",
        flush=True
    )

    print(
        json.dumps(
            results[0],
            ensure_ascii=False,
            indent=2
        ),
        flush=True
    )


print(
    "=" * 70,
    flush=True
)