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
# COLLECTION SETTINGS
# ============================================================

BATCH_SIZE = 1000

SAVE_EVERY = 600

MIN_DELAY = 0.1
MAX_DELAY = 0.2

REQUEST_TIMEOUT = (5, 15)

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
# CREATE OUTPUT DIRECTORY
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

    except Exception as error:

        print(
            f"Could not load {filename}: {error}",
            flush=True
        )

        return default


# ============================================================
# NUMBER PARSER
# ============================================================

def parse_number(value):

    value = clean_text(value)

    if not value:
        return None

    try:

        value = (
            value
            .replace(",", "")
            .strip()
        )

        return float(value)

    except Exception:

        return None


# ============================================================
# GPA PARSER
# ============================================================

def parse_gpa(value):

    value = clean_text(value)

    if not value:
        return None

    upper = value.upper()

    # Examples:
    # GPA=5.00
    # GPA = 5.00
    # GPA 5.00

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

    elif "GPA" in upper:

        value = upper.split(
            "GPA",
            1
        )[1].replace(
            "=",
            ""
        ).strip()

    try:

        return float(
            value.split()[0]
        )

    except Exception:

        return None


# ============================================================
# SUBJECT RESULT PARSER
# ============================================================

def parse_subject_result(value):

    value = clean_text(value)

    mark = None
    grade = ""

    if not value:
        return mark, grade

    # Example:
    # 85 (A+)
    # 78(A)
    # 67 (A-)

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

        number = parse_number(
            mark_text
        )

        if number is not None:
            mark = int(number)

        grade = grade_text

    else:

        number = parse_number(
            value
        )

        if number is not None:
            mark = int(number)

    return mark, grade


# ============================================================
# FIND VALUE AFTER LABEL
# ============================================================

def find_value_after_label(
    values,
    label
):

    label = clean_text(
        label
    ).lower()

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
# FIND LABEL VALUE MORE FLEXIBLY
# ============================================================

def find_label_value(
    soup,
    labels
):

    labels = [
        clean_text(x).lower()
        for x in labels
    ]

    # --------------------------------------------------------
    # TABLE ROW METHOD
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

        if not values:
            continue

        for index, value in enumerate(values):

            normalized = value.lower()

            for label in labels:

                if normalized == label:

                    if index + 1 < len(values):

                        found = clean_text(
                            values[index + 1]
                        )

                        if found:
                            return found

    return ""


# ============================================================
# PARSE RESULT PAGE
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

        "board": BOARD,

        "group": group_name,

        "session": "",

        "type": "",

        "institute": "",

        "district": "",

        "thana": "",

        "gpa": None,

        "total_score": 0,

        "subjects": []
    }


    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    result["roll"] = (
        find_label_value(
            soup,
            [
                "Roll No",
                "Roll",
                "Roll Number"
            ]
        )
        or str(requested_roll)
    )

    result["name"] = find_label_value(
        soup,
        [
            "Name",
            "Student Name"
        ]
    )

    result["board"] = (
        find_label_value(
            soup,
            [
                "Board"
            ]
        )
        or BOARD
    )

    result["group"] = (
        find_label_value(
            soup,
            [
                "Group"
            ]
        )
        or group_name
    )

    result["session"] = find_label_value(
        soup,
        [
            "Session"
        ]
    )

    result["type"] = find_label_value(
        soup,
        [
            "Type"
        ]
    )

    result["institute"] = find_label_value(
        soup,
        [
            "Institute",
            "Institution",
            "Institution Name",
            "School & College",
            "College"
        ]
    )

    result["district"] = find_label_value(
        soup,
        [
            "District"
        ]
    )


    # ========================================================
    # GPA
    # ========================================================

    result_text = ""

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

        value = find_value_after_label(
            values,
            "Result"
        )

        if value:

            result_text = value

            gpa = parse_gpa(
                value
            )

            if gpa is not None:

                result["gpa"] = gpa


    # ========================================================
    # GPA FALLBACK FROM FULL PAGE
    # ========================================================

    if result["gpa"] is None:

        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

        upper = page_text.upper()

        for marker in [
            "GPA=",
            "GPA =",
            "GPA"
        ]:

            if marker in upper:

                try:

                    part = upper.split(
                        marker,
                        1
                    )[1]

                    part = (
                        part
                        .replace(
                            "=",
                            " "
                        )
                        .strip()
                    )

                    token = (
                        part
                        .split()[0]
                    )

                    gpa = float(
                        token
                    )

                    if 0 <= gpa <= 5:

                        result["gpa"] = gpa

                        break

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


            # ------------------------------------------------
            # FIND SUBJECT CODE
            # ------------------------------------------------

            code = ""

            for value in values:

                cleaned = clean_text(
                    value
                )

                if (
                    cleaned.isdigit()
                    and 3 <= len(cleaned) <= 5
                ):

                    code = cleaned

                    break

            if not code:
                continue


            code_index = values.index(
                code
            )

            # ------------------------------------------------
            # SUBJECT NAME
            # ------------------------------------------------

            subject = ""

            if code_index + 1 < len(values):

                subject = values[
                    code_index + 1
                ]

            if not subject:
                continue


            # ------------------------------------------------
            # MARK / GRADE
            # ------------------------------------------------

            mark = None
            grade = ""

            if code_index + 2 < len(values):

                mark, grade = (
                    parse_subject_result(
                        values[
                            code_index + 2
                        ]
                    )
                )


            # ------------------------------------------------
            # AVOID DUPLICATES
            # ------------------------------------------------

            key = (
                code,
                subject
            )

            if key in seen:
                continue

            seen.add(
                key
            )


            result["subjects"].append({

                "code": code,

                "subject": subject,

                "mark": mark,

                "grade": grade
            })


    # ========================================================
    # CALCULATE TOTAL SCORE
    # ========================================================

    total_score = 0

    for subject in result["subjects"]:

        mark = subject.get(
            "mark"
        )

        if isinstance(
            mark,
            (int, float)
        ):

            total_score += mark


    result["total_score"] = (
        total_score
    )


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
        "district",
        "thana"
    ]:

        result[key] = clean_text(
            result[key]
        )


    return result


# ============================================================
# GENERATE ROLLS
# ============================================================

def generate_rolls():

    # IMPORTANT:
    # This order must NOT be changed.

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
# TOTAL TARGET
# ============================================================

total_target = sum(
    end - start + 1
    for start, end in ROLL_RANGES.values()
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
    f"Total target rolls: {total_target:,}",
    flush=True
)

print(
    f"Already collected: {len(existing_rolls):,}",
    flush=True
)

print(
    f"Remaining: "
    f"{max(total_target - len(existing_rolls), 0):,}",
    flush=True
)

print(
    f"Batch size: {BATCH_SIZE:,}",
    flush=True
)

print(
    f"Save every: {SAVE_EVERY} successful students",
    flush=True
)

print(
    "",
    flush=True
)

print(
    "GROUP ORDER:",
    flush=True
)

for group_name, (
    start,
    end
) in ROLL_RANGES.items():

    print(
        f"  {group_name}: "
        f"{start:,} - {end:,}",
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
    "Opening SSC Individual Result page...",
    flush=True
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

except requests.exceptions.Timeout:

    raise SystemExit(
        "ERROR: Opening result page timed out."
    )

except requests.RequestException as error:

    raise SystemExit(
        f"ERROR: Could not open result page: {error}"
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
    form_method,
    flush=True
)

print(
    "Form URL:",
    FORM_ACTION_URL,
    flush=True
)


# ============================================================
# COLLECT FORM INPUTS
# ============================================================

base_form_data = {}

for inp in form.find_all("input"):

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
        "image"
    ]:

        continue

    if input_type in [
        "checkbox",
        "radio"
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
# SELECT FIELDS
# ============================================================

for select in form.find_all("select"):

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
        "button2": "Submit"
    }


print(
    "Submit fields:",
    submit_fields,
    flush=True
)


# ============================================================
# COUNTERS
# ============================================================

processed_this_run = 0

success_this_run = 0

not_found_this_run = 0

error_this_run = 0


# ============================================================
# MAIN COLLECTION
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
    # BATCH LIMIT
    # --------------------------------------------------------

    if (
        processed_this_run
        >= BATCH_SIZE
    ):

        break


    processed_this_run += 1


    print(
        "\n" + "-" * 70,
        flush=True
    )

    print(
        f"[{processed_this_run}/{BATCH_SIZE}] "
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
                "Referer": page.url,
                "Origin":
                    "https://sresult.bise-ctg.gov.bd",
                "Content-Type":
                    "application/x-www-form-urlencoded",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

    except requests.exceptions.Timeout:

        print(
            f"TIMEOUT: {roll} — skipping",
            flush=True
        )

        error_this_run += 1

        failed_rolls.append({
            "roll": roll,
            "group": group_name,
            "reason": "timeout"
        })

        continue

    except requests.exceptions.RequestException as error:

        print(
            f"REQUEST ERROR: {roll} — {error}",
            flush=True
        )

        error_this_run += 1

        failed_rolls.append({
            "roll": roll,
            "group": group_name,
            "reason": str(error)
        })

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
            f"HTTP ERROR: {response.status_code}",
            flush=True
        )

        error_this_run += 1

        failed_rolls.append({
            "roll": roll,
            "group": group_name,
            "reason":
                f"HTTP {response.status_code}"
        })

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

    except Exception as error:

        print(
            f"PARSING ERROR: "
            f"{roll} — {error}",
            flush=True
        )

        error_this_run += 1

        failed_rolls.append({
            "roll": roll,
            "group": group_name,
            "reason":
                f"parse error: {error}"
        })

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
            "total_score",
            0
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
    # ADD TO MEMORY
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
    # CHECKPOINT
    # ========================================================

    if (
        success_this_run > 0
        and success_this_run % SAVE_EVERY == 0
    ):

        print(
            "\n" + "=" * 70,
            flush=True
        )

        print(
            "SAVING CHECKPOINT",
            flush=True
        )

        print(
            f"New students this run: "
            f"{success_this_run:,}",
            flush=True
        )

        print(
            f"Total students: "
            f"{len(students):,}",
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
            "CHECKPOINT SAVED",
            flush=True
        )

        print(
            "=" * 70,
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
    total_target - len(existing_rolls),
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
        processed_this_run,

    "successful_this_run":
        success_this_run,

    "not_found_this_run":
        not_found_this_run,

    "errors_this_run":
        error_this_run,

    "batch_size":
        BATCH_SIZE,

    "save_every":
        SAVE_EVERY,

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
    processed_this_run,
    flush=True
)

print(
    "Successful:",
    success_this_run,
    flush=True
)

print(
    "Not found:",
    not_found_this_run,
    flush=True
)

print(
    "Errors:",
    error_this_run,
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