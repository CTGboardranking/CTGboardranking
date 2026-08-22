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
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
session.headers.update(headers)


# ============================================================
# HELPER
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        value.split()
    ).strip()


def save_json(filename, data):

    with open(
        os.path.join(
            OUTPUT_DIR,
            filename
        ),
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# 1. OPEN INDIVIDUAL PAGE
# ============================================================

print("Opening SSC Individual Result page...")

try:

    page = session.get(
        INDIVIDUAL_URL,
        headers={
            "Referer": BASE_URL
        },
        timeout=30,
        allow_redirects=True
    )

except requests.RequestException as e:

    print(
        "GET Error:",
        repr(e)
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
) as f:

    f.write(page.text)


if page.status_code != 200:

    raise SystemExit(
        f"Could not open individual result page: "
        f"HTTP {page.status_code}"
    )


# ============================================================
# 2. FIND FORM
# ============================================================

soup = BeautifulSoup(
    page.text,
    "html.parser"
)

form = soup.find("form")

if not form:

    print(
        "ERROR: No form found."
    )

    raise SystemExit(1)


form_action = form.get(
    "action",
    ""
).strip()

form_method = form.get(
    "method",
    "get"
).strip().lower()

FORM_ACTION_URL = urljoin(
    page.url,
    form_action
)


print("\n===== FORM =====")

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
for inp in form.find_all("input"):

    name = inp.get("name")

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

        if not inp.has_attr("checked"):
            continue

    base_form_data[name] = value


# ---------- SELECT ----------
for select in form.find_all("select"):

    name = select.get("name")

    if not name:
        continue

    selected = select.find(
        "option",
        selected=True
    )

    if selected:

        value = selected.get(
            "value",
            selected.get_text(strip=True)
        )

    else:

        first = select.find(
            "option"
        )

        if first:

            value = first.get(
                "value",
                first.get_text(strip=True)
            )

        else:

            value = ""

    base_form_data[name] = value


# ---------- TEXTAREA ----------
for textarea in form.find_all("textarea"):

    name = textarea.get("name")

    if not name:
        continue

    base_form_data[name] = (
        textarea.get_text()
    )


# ============================================================
# 4. FIND SUBMIT FIELD
# ============================================================

submit_fields = {}

for button in form.find_all(
    ["input", "button"]
):

    button_type = button.get(
        "type",
        ""
    ).lower()

    name = button.get("name")

    if (
        button_type == "submit"
        and name
    ):

        value = button.get(
            "value",
            button.get_text(strip=True)
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
# 5. SAVE BASE FORM DATA
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
# 6. RESULT PARSER
# ============================================================

def parse_result(
    html,
    roll
):

    result_soup = BeautifulSoup(
        html,
        "html.parser"
    )

    result_data = {

        "roll": roll,

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
    # BASIC DATA
    # ========================================================

    rows = result_soup.find_all("tr")

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
# Roll + Name
# ----------------------------------------------------

if "Roll No" in values:

    idx = values.index("Roll No")

    # Expected:
    # Roll No | 100001 | Name | SHUVOJIT GHOSH

    if idx + 1 < len(values):
        result_data["roll"] = values[idx + 1]

    # Find "Name" anywhere after Roll No
    for i in range(
        idx + 1,
        len(values) - 1
    ):

        if values[i].strip().lower() == "name":

            result_data["name"] = values[i + 1]

            break
        


        # ----------------------------------------------------
        # Board
        # ----------------------------------------------------

        if "Board" in values:

            idx = values.index(
                "Board"
            )

            if idx + 1 < len(values):

                result_data["board"] = (
                    values[idx + 1]
                )


        # ----------------------------------------------------
        # Group
        # ----------------------------------------------------

        if "Group" in values:

            idx = values.index(
                "Group"
            )

            if idx + 1 < len(values):

                result_data["group"] = (
                    values[idx + 1]
                )


        # ----------------------------------------------------
        # Session
        # ----------------------------------------------------

        if "Session" in values:

            idx = values.index(
                "Session"
            )

            if idx + 1 < len(values):

                result_data["session"] = (
                    values[idx + 1]
                )


        # ----------------------------------------------------
        # Type
        # ----------------------------------------------------

        if "Type" in values:

            idx = values.index(
                "Type"
            )

            if idx + 1 < len(values):

                result_data["type"] = (
                    values[idx + 1]
                )


        # ----------------------------------------------------
        # Institute
        # ----------------------------------------------------

        if "Institute" in values:

            idx = values.index(
                "Institute"
            )

            if idx + 1 < len(values):

                result_data["institute"] = (
                    values[idx + 1]
                )


        # ----------------------------------------------------
        # Result / GPA
        # ----------------------------------------------------

        if "Result" in values:

            idx = values.index(
                "Result"
            )

            if idx + 1 < len(values):

                result_value = values[
                    idx + 1
                ]

                if "GPA=" in result_value:

                    try:

                        result_data["gpa"] = float(
                            result_value
                            .split(
                                "GPA=",
                                1
                            )[1]
                            .strip()
                        )

                    except ValueError:

                        pass


    # ========================================================
    # SUBJECT TABLE
    # ========================================================

    for table in result_soup.find_all(
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

            grade_mark = values[2]

            mark = None

            grade = ""


            # Example:
            # 127(A-)
            # 158(A)
            # 096(A+)

            if "(" in grade_mark:

                mark_text = (
                    grade_mark
                    .split(
                        "(",
                        1
                    )[0]
                    .strip()
                )

                grade_text = (
                    grade_mark
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
                        grade_mark
                    )

                except ValueError:

                    mark = None


            result_data[
                "subjects"
            ].append({

                "code": code,

                "subject": subject,

                "mark": mark,

                "grade": grade
            })


    return result_data


# ============================================================
# 7. COLLECT MULTIPLE STUDENTS
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
    "========================================\n"
)


for index, roll in enumerate(
    TEST_ROLLS,
    start=1
):

    print(
        f"\n===== STUDENT {index}/{len(TEST_ROLLS)} ====="
    )

    print(
        "Submitting Roll:",
        roll
    )

    # --------------------------------------------------------
    # Fresh copy of form data
    # --------------------------------------------------------

    form_data = dict(
        base_form_data
    )

    form_data["roll"] = roll

    # Add submit field
    for key, value in submit_fields.items():

        form_data[key] = value


    # Save form for this roll
    save_json(
        f"form_data_{roll}.json",
        form_data
    )


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    post_headers = {
        "Referer": page.url,

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

    except requests.RequestException as e:

        print(
            "POST Error:",
            repr(e)
        )

        failed_rolls.append({
            "roll": roll,
            "error": repr(e)
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


    # --------------------------------------------------------
    # Save response HTML
    # --------------------------------------------------------

    with open(
        os.path.join(
            OUTPUT_DIR,
            f"result_page_{roll}.html"
        ),
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            result.text
        )


    # --------------------------------------------------------
    # Save headers
    # --------------------------------------------------------

    save_json(
        f"response_headers_{roll}.json",
        dict(result.headers)
    )


    # --------------------------------------------------------
    # Save redirect history
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # HTTP error
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Parse
    # --------------------------------------------------------

    parsed = parse_result(
        result.text,
        roll
    )


    # --------------------------------------------------------
    # Check result
    # --------------------------------------------------------

    if not parsed["institute"]:

        print(
            "WARNING: No institute found."
        )

        failed_rolls.append({

            "roll": roll,

            "error":
                "Result data not found"
        })

        continue


    # --------------------------------------------------------
    # Save individual parsed result
    # --------------------------------------------------------

    save_json(
        f"parsed_result_{roll}.json",
        parsed
    )


    # Keep compatibility with old pipeline
    save_json(
        "parsed_result.json",
        parsed
    )


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
        "GPA:",
        parsed["gpa"]
    )

    print(
        "Subjects:",
        len(parsed["subjects"])
    )


# ============================================================
# 8. SAVE STUDENTS.JSON
# ============================================================

save_json(
    "students.json",
    students
)


# ============================================================
# 9. SAVE COLLECTION SUMMARY
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
# 10. SAVE COOKIES
# ============================================================

cookies = {}

for cookie in session.cookies:

    cookies[cookie.name] = cookie.value


save_json(
    "cookies.json",
    cookies
)


# ============================================================
# 11. FINAL OUTPUT
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


# At least one result is required
if not students:

    raise SystemExit(
        "No student results were collected."
    )

if not students:

    raise SystemExit(
        "No student results were collected."