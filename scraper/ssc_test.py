import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"
INDIVIDUAL_URL = BASE_URL + "individual/"

TEST_ROLLS = [
    "100001",
    "100002",
    "100003",
    "100004",
    "100005"
]

OUTPUT_DIR = "scraper"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# HEADERS
# ============================================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
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
    headers
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

    filepath = os.path.join(
        OUTPUT_DIR,
        filename
    )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# PARSE GPA
# ============================================================

def parse_gpa(value):

    value = clean_text(value)

    if not value:
        return None

    # Examples:
    # GPA=5.00
    # GPA = 5.00
    # 5.00

    if "GPA=" in value:

        value = value.split(
            "GPA=",
            1
        )[1].strip()

    elif "GPA =" in value:

        value = value.split(
            "GPA =",
            1
        )[1].strip()

    try:

        return float(
            value
        )

    except ValueError:

        return None


# ============================================================
# PARSE SUBJECT MARK
# ============================================================

def parse_subject_result(
    value
):

    value = clean_text(
        value
    )

    mark = None
    grade = ""

    # Example:
    # 127(A-)
    # 158(A)
    # 096(A+)

    if "(" in value:

        mark_text = (
            value
            .split(
                "(",
                1
            )[0]
            .strip()
        )

        grade_text = (
            value
            .split(
                "(",
                1
            )[1]
            .replace(
                ")",
                ""
            )
            .strip()
        )

        try:

            mark = int(
                mark_text
            )

        except ValueError:

            mark = None

        grade = grade_text

    else:

        try:

            mark = int(
                value
            )

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

    label_lower = label.lower()

    for index, value in enumerate(
        values
    ):

        if clean_text(value).lower() == label_lower:

            if index + 1 < len(values):

                return clean_text(
                    values[index + 1]
                )

    return ""


# ============================================================
# PARSE STUDENT RESULT
# ============================================================

def parse_result(
    html,
    requested_roll
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    result_data = {

        "roll": requested_roll,

        "name": "",

        "board": "",

        "group": "",

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

    rows = soup.find_all(
        "tr"
    )

    for row in rows:

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


        # ----------------------------------------------------
        # ROLL
        # ----------------------------------------------------

        if "Roll No" in values:

            roll_value = find_value_after_label(
                values,
                "Roll No"
            )

            if roll_value:

                result_data["roll"] = (
                    roll_value
                )


        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if "Name" in values:

            name_value = find_value_after_label(
                values,
                "Name"
            )

            if name_value:

                result_data["name"] = (
                    name_value
                )


        # ----------------------------------------------------
        # BOARD
        # ----------------------------------------------------

        if "Board" in values:

            board_value = find_value_after_label(
                values,
                "Board"
            )

            if board_value:

                result_data["board"] = (
                    board_value
                )


        # ----------------------------------------------------
        # GROUP
        # ----------------------------------------------------

        if "Group" in values:

            group_value = find_value_after_label(
                values,
                "Group"
            )

            if group_value:

                result_data["group"] = (
                    group_value
                )


        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        if "Session" in values:

            session_value = find_value_after_label(
                values,
                "Session"
            )

            if session_value:

                result_data["session"] = (
                    session_value
                )


        # ----------------------------------------------------
        # TYPE
        # ----------------------------------------------------

        if "Type" in values:

            type_value = find_value_after_label(
                values,
                "Type"
            )

            if type_value:

                result_data["type"] = (
                    type_value
                )


        # ----------------------------------------------------
        # INSTITUTE
        # ----------------------------------------------------

        if "Institute" in values:

            institute_value = find_value_after_label(
                values,
                "Institute"
            )

            if institute_value:

                result_data["institute"] = (
                    institute_value
                )


        # ----------------------------------------------------
        # DISTRICT
        # ----------------------------------------------------

        if "District" in values:

            district_value = find_value_after_label(
                values,
                "District"
            )

            if district_value:

                result_data["district"] = (
                    district_value
                )


        # ----------------------------------------------------
        # RESULT / GPA
        # ----------------------------------------------------

        if "Result" in values:

            result_value = find_value_after_label(
                values,
                "Result"
            )

            gpa = parse_gpa(
                result_value
            )

            if gpa is not None:

                result_data["gpa"] = gpa


    # ========================================================
    # FALLBACK: SEARCH PAGE TEXT FOR GPA
    # ========================================================

    if result_data["gpa"] is None:

        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

        if "GPA=" in page_text:

            try:

                gpa_text = (
                    page_text
                    .split(
                        "GPA=",
                        1
                    )[1]
                    .split(
                        " ",
                        1
                    )[0]
                )

                result_data["gpa"] = float(
                    gpa_text
                )

            except (
                ValueError,
                IndexError
            ):

                pass


    # ========================================================
    # SUBJECT TABLE
    # ========================================================

    seen_subjects = set()

    for table in soup.find_all(
        "table"
    ):

        table_rows = table.find_all(
            "tr"
        )

        for row in table_rows:

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

            # Subject code must be numeric
            if not code.isdigit():
                continue


            subject = values[1]

            mark_grade_value = values[2]

            mark, grade = parse_subject_result(
                mark_grade_value
            )


            # Avoid duplicate subjects
            subject_key = (
                code,
                subject
            )

            if subject_key in seen_subjects:
                continue

            seen_subjects.add(
                subject_key
            )


            result_data["subjects"].append({

                "code": code,

                "subject": subject,

                "mark": mark,

                "grade": grade
            })


    # ========================================================
    # CLEAN FINAL VALUES
    # ========================================================

    result_data["roll"] = clean_text(
        result_data["roll"]
    )

    result_data["name"] = clean_text(
        result_data["name"]
    )

    result_data["board"] = clean_text(
        result_data["board"]
    )

    result_data["group"] = clean_text(
        result_data["group"]
    )

    result_data["session"] = clean_text(
        result_data["session"]
    )

    result_data["type"] = clean_text(
        result_data["type"]
    )

    result_data["institute"] = clean_text(
        result_data["institute"]
    )

    result_data["district"] = clean_text(
        result_data["district"]
    )


    return result_data


# ============================================================
# 1. OPEN INDIVIDUAL RESULT PAGE
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

        timeout=30,

        allow_redirects=True
    )

except requests.RequestException as error:

    print(
        "GET Error:",
        repr(error)
    )

    raise SystemExit(1)


print(
    "GET Status:",
    page.status_code
)

print(
    "GET Final URL:",
    page.url
)

print(
    "GET Page Size:",
    len(page.content)
)


with open(
    os.path.join(
        OUTPUT_DIR,
        "individual_page.html"
    ),
    "w",
    encoding="utf-8"
) as file:

    file.write(
        page.text
    )


if page.status_code != 200:

    raise SystemExit(
        "Could not open SSC result page."
    )


# ============================================================
# 2. FIND FORM
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
        "ERROR: No form found."
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
        "get"
    )
).lower()


FORM_ACTION_URL = urljoin(
    page.url,
    form_action
)


print(
    "\n===== FORM ====="
)

print(
    "Method:",
    form_method
)

print(
    "Action:",
    form_action
)

print(
    "Resolved URL:",
    FORM_ACTION_URL
)


# ============================================================
# 3. COLLECT FORM FIELDS
# ============================================================

base_form_data = {}


# ---------- INPUT ----------
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

    value = inp.get(
        "value",
        ""
    )

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


    base_form_data[name] = value


# ---------- SELECT ----------
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


    if selected:

        value = selected.get(
            "value",
            selected.get_text(
                strip=True
            )
        )

    else:

        first = select.find(
            "option"
        )

        if first:

            value = first.get(
                "value",
                first.get_text(
                    strip=True
                )
            )

        else:

            value = ""


    base_form_data[name] = value


# ---------- TEXTAREA ----------
for textarea in form.find_all(
    "textarea"
):

    name = textarea.get(
        "name"
    )

    if not name:
        continue

    base_form_data[name] = (
        textarea.get_text()
    )


# ============================================================
# 4. SUBMIT FIELD
# ============================================================

submit_fields = {}


for button in form.find_all(
    ["input", "button"]
):

    button_type = button.get(
        "type",
        ""
    ).lower()

    name = button.get(
        "name"
    )


    if (
        button_type == "submit"
        and name
    ):

        value = button.get(
            "value",
            button.get_text(
                strip=True
            )
        )

        submit_fields[name] = value


if not submit_fields:

    submit_fields = {
        "button2": "Submit"
    }


print(
    "\nSubmit fields:",
    submit_fields
)


# ============================================================
# 5. SAVE FORM DATA
# ============================================================

save_json(
    "form_data.json",
    {
        "form_action": FORM_ACTION_URL,
        "method": form_method,
        "fields": base_form_data,
        "submit_fields": submit_fields
    }
)


# ============================================================
# 6. COLLECT MULTIPLE STUDENTS
# ============================================================

students = []

successful_rolls = []

failed_rolls = []


print(
    "\n========================================"
)

print(
    "STARTING MULTI-ROLL COLLECTION"
)

print(
    "Rolls:",
    ", ".join(TEST_ROLLS)
)

print(
    "========================================"
)


for index, roll in enumerate(
    TEST_ROLLS,
    start=1
):

    print(
        f"\n===== STUDENT "
        f"{index}/{len(TEST_ROLLS)} ====="
    )

    print(
        "Submitting Roll:",
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


    save_json(
        f"form_data_{roll}.json",
        form_data
    )


    # ========================================================
    # POST
    # ========================================================

    post_headers = {

        "Referer":
            page.url,

        "Origin":
            "https://sresult.bise-ctg.gov.bd",

        "Content-Type":
            "application/x-www-form-urlencoded",

        "Accept":
            (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            )
    }


    try:

        result = session.post(

            FORM_ACTION_URL,

            data=form_data,

            headers=post_headers,

            timeout=30,

            allow_redirects=True
        )

    except requests.RequestException as error:

        print(
            "POST Error:",
            repr(error)
        )

        failed_rolls.append({

            "roll": roll,

            "error": repr(error)
        })

        continue


    print(
        "POST Status:",
        result.status_code
    )

    print(
        "Final URL:",
        result.url
    )

    print(
        "Response Size:",
        len(result.content)
    )


    # ========================================================
    # SAVE HTML
    # ========================================================

    with open(
        os.path.join(
            OUTPUT_DIR,
            f"result_page_{roll}.html"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            result.text
        )


    # ========================================================
    # SAVE HEADERS
    # ========================================================

    save_json(
        f"response_headers_{roll}.json",
        dict(result.headers)
    )


    # ========================================================
    # SAVE REDIRECT HISTORY
    # ========================================================

    history = []


    for response in result.history:

        history.append({

            "status_code":
                response.status_code,

            "url":
                response.url,

            "headers":
                dict(response.headers)
        })


    save_json(
        f"response_history_{roll}.json",
        history
    )


    # ========================================================
    # HTTP ERROR
    # ========================================================

    if result.status_code >= 400:

        print(
            "HTTP ERROR:",
            result.status_code
        )


        save_json(
            f"error_{roll}.json",
            {

                "status_code":
                    result.status_code,

                "url":
                    result.url,

                "body":
                    result.text[:10000]
            }
        )


        failed_rolls.append({

            "roll": roll,

            "error":
                f"HTTP {result.status_code}"
        })


        continue


    # ========================================================
    # PARSE RESULT
    # ========================================================

    parsed = parse_result(
        result.text,
        roll
    )


    # ========================================================
    # CHECK RESULT
    # ========================================================

    if not parsed["institute"]:

        print(
            "WARNING: No institute found."
        )


        failed_rolls.append({

            "roll": roll,

            "error":
                "Result data not found"
        })


        save_json(
            f"failed_result_{roll}.json",
            parsed
        )


        continue


    # ========================================================
    # SAVE PARSED RESULT
    # ========================================================

    save_json(
        f"parsed_result_{roll}.json",
        parsed
    )


    # Compatibility file
    save_json(
        "parsed_result.json",
        parsed
    )


    # ========================================================
    # ADD STUDENT
    # ========================================================

    students.append(
        parsed
    )

    successful_rolls.append(
        roll
    )


    print(
        "\nStudent found:"
    )

    print(
        "Roll:",
        parsed["roll"]
    )

    print(
        "Name:",
        parsed["name"]
    )

    print(
        "Institute:",
        parsed["institute"]
    )

    print(
        "District:",
        parsed["district"]
    )

    print(
        "GPA:",
        parsed["gpa"]
    )

    print(
        "Subjects:",
        len(parsed["subjects"])
    )


# ============================================================
# 7. SAVE STUDENTS.JSON
# ============================================================

save_json(
    "students.json",
    students
)


# ============================================================
# 8. COLLECTION SUMMARY
# ============================================================

summary = {

    "requested_rolls":
        TEST_ROLLS,

    "successful_rolls":
        successful_rolls,

    "failed_rolls":
        failed_rolls,

    "total_requested":
        len(TEST_ROLLS),

    "total_successful":
        len(successful_rolls),

    "total_failed":
        len(failed_rolls)
}


save_json(
    "student_collection_summary.json",
    summary
)


# ============================================================
# 9. SAVE COOKIES
# ============================================================

cookies = {}


for cookie in session.cookies:

    cookies[cookie.name] = cookie.value


save_json(
    "cookies.json",
    cookies
)


# ============================================================
# 10. FINAL OUTPUT
# ============================================================

print(
    "\n========================================"
)

print(
    "===== STUDENT COLLECTION COMPLETE ====="
)

print(
    "========================================"
)

print(
    "Requested:",
    len(TEST_ROLLS)
)

print(
    "Successful:",
    len(successful_rolls)
)

print(
    "Failed:",
    len(failed_rolls)
)


if successful_rolls:

    print(
        "\nSuccessful rolls:"
    )

    for roll in successful_rolls:

        print(
            "  ✓",
            roll
        )


if failed_rolls:

    print(
        "\nFailed rolls:"
    )

    for item in failed_rolls:

        print(
            "  ✗",
            item["roll"],
            "-",
            item["error"]
        )


print(
    "\nSaved:",
    "scraper/students.json"
)

print(
    "Saved:",
    "scraper/student_collection_summary.json"
)

print(
    "\n===== DONE ====="
)


# ============================================================
# REQUIRE AT LEAST ONE RESULT
# ============================================================

if not students:

    raise SystemExit(
        "No student results were collected."
    )