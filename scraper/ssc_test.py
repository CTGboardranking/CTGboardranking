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

ROLL = "100001"

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
# 1. OPEN INDIVIDUAL RESULT PAGE
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
    print("GET Error:", repr(e))
    raise SystemExit(1)


print("GET Status:", page.status_code)
print("GET Final URL:", page.url)
print("GET Page Size:", len(page.content))


with open(
    os.path.join(OUTPUT_DIR, "individual_page.html"),
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
    print("ERROR: No form found.")
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
print("Method:", form_method)
print("Action:", form_action)
print("Resolved URL:", FORM_ACTION_URL)


# ============================================================
# 3. COLLECT FORM FIELDS
# ============================================================

form_data = {}


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

    form_data[name] = value


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
        first = select.find("option")

        if first:
            value = first.get(
                "value",
                first.get_text(strip=True)
            )
        else:
            value = ""

    form_data[name] = value


# ---------- TEXTAREA ----------
for textarea in form.find_all("textarea"):

    name = textarea.get("name")

    if not name:
        continue

    form_data[name] = textarea.get_text()


# ============================================================
# 4. ADD ROLL
# ============================================================

form_data["roll"] = ROLL


# ============================================================
# 5. SUBMIT BUTTON
# ============================================================

submit_found = False

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

        form_data[name] = value

        submit_found = True

        print(
            "Submit field:",
            name,
            "=",
            value
        )

        break


# Existing SSC form fallback
if not submit_found:

    form_data["button2"] = "Submit"

    print(
        "Using submit fallback: "
        "button2=Submit"
    )


# ============================================================
# 6. SAVE FORM DATA
# ============================================================

with open(
    os.path.join(
        OUTPUT_DIR,
        "form_data.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        form_data,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\nPOST DATA:")

for key, value in form_data.items():
    print(
        f"{key}: {value}"
    )


# ============================================================
# 7. POST
# ============================================================

print("\nSubmitting Roll:", ROLL)
print("POST URL:", FORM_ACTION_URL)

post_headers = {
    "Referer": page.url,
    "Origin": "https://sresult.bise-ctg.gov.bd",
    "Content-Type": (
        "application/x-www-form-urlencoded"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
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

    print("POST Error:", repr(e))

    with open(
        os.path.join(
            OUTPUT_DIR,
            "post_exception.txt"
        ),
        "w",
        encoding="utf-8"
    ) as f:
        f.write(repr(e))

    raise SystemExit(1)


# ============================================================
# 8. SAVE RESPONSE
# ============================================================

print("\n===== POST RESPONSE =====")

print(
    "Status:",
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


with open(
    os.path.join(
        OUTPUT_DIR,
        "result_page.html"
    ),
    "w",
    encoding="utf-8"
) as f:
    f.write(result.text)


with open(
    os.path.join(
        OUTPUT_DIR,
        "response_headers.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        dict(result.headers),
        f,
        ensure_ascii=False,
        indent=2
    )


history = []

for response in result.history:

    history.append({
        "status_code": response.status_code,
        "url": response.url,
        "headers": dict(response.headers)
    })


with open(
    os.path.join(
        OUTPUT_DIR,
        "response_history.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        history,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 9. CHECK RESPONSE
# ============================================================

if result.status_code >= 400:

    print("\n===== ERROR BODY =====")
    print(result.text[:10000])

    with open(
        os.path.join(
            OUTPUT_DIR,
            "error_body.html"
        ),
        "w",
        encoding="utf-8"
    ) as f:
        f.write(result.text)

    raise SystemExit(
        f"POST failed: HTTP {result.status_code}"
    )


# ============================================================
# 10. PARSE RESULT
# ============================================================

result_soup = BeautifulSoup(
    result.text,
    "html.parser"
)

print("\n===== PARSING RESULT =====")


# ------------------------------------------------------------
# Helper function
# ------------------------------------------------------------

def clean_text(value):
    if value is None:
        return ""
    return " ".join(
        value.split()
    ).strip()


# ============================================================
# 11. EXTRACT BASIC RESULT DATA
# ============================================================

result_data = {
    "roll": ROLL,
    "board": "",
    "group": "",
    "session": "",
    "type": "",
    "institute": "",
    "gpa": None,
    "subjects": []
}


# Search all table rows
rows = result_soup.find_all("tr")


for row in rows:

    cells = row.find_all(
        ["th", "td"]
    )

    values = [
        clean_text(
            cell.get_text(" ", strip=True)
        )
        for cell in cells
    ]

    if not values:
        continue

    row_text = " | ".join(values)

    # Board
    if "Board" in values:
        idx = values.index("Board")

        if idx + 1 < len(values):
            result_data["board"] = values[idx + 1]


    # Group
    if "Group" in values:
        idx = values.index("Group")

        if idx + 1 < len(values):
            result_data["group"] = values[idx + 1]


    # Session
    if "Session" in values:
        idx = values.index("Session")

        if idx + 1 < len(values):
            result_data["session"] = values[idx + 1]


    # Type
    if "Type" in values:
        idx = values.index("Type")

        if idx + 1 < len(values):
            result_data["type"] = values[idx + 1]


    # Institute
    if "Institute" in values:
        idx = values.index("Institute")

        if idx + 1 < len(values):
            result_data["institute"] = values[idx + 1]


    # Result / GPA
    if "Result" in values:
        idx = values.index("Result")

        if idx + 1 < len(values):

            result_value = values[idx + 1]

            if "GPA=" in result_value:

                try:
                    result_data["gpa"] = float(
                        result_value
                        .split("GPA=", 1)[1]
                        .strip()
                    )
                except ValueError:
                    pass


# ============================================================
# 12. EXTRACT SUBJECT TABLE
# ============================================================

for table in result_soup.find_all("table"):

    table_rows = table.find_all("tr")

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

        # Subject codes are numeric
        if not code.isdigit():
            continue

        subject = values[1]
        grade_mark = values[2]

        mark = None
        grade = ""

        # Example:
        # 127(A-)
        # 158(A )
        # 096(A+)

        if "(" in grade_mark:

            mark_text = (
                grade_mark
                .split("(", 1)[0]
                .strip()
            )

            grade_text = (
                grade_mark
                .split("(", 1)[1]
                .replace(")", "")
                .strip()
            )

            try:
                mark = int(mark_text)
            except ValueError:
                mark = None

            grade = grade_text

        else:

            try:
                mark = int(grade_mark)
            except ValueError:
                mark = None


        result_data["subjects"].append({
            "code": code,
            "subject": subject,
            "mark": mark,
            "grade": grade
        })


# ============================================================
# 13. SAVE STRUCTURED RESULT
# ============================================================

output_file = os.path.join(
    OUTPUT_DIR,
    "parsed_result.json"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result_data,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 14. DISPLAY RESULT
# ============================================================

print("\n===== PARSED RESULT =====")

print(
    json.dumps(
        result_data,
        ensure_ascii=False,
        indent=2
    )
)


# ============================================================
# 15. FINAL
# ============================================================

print("\n===== FILES =====")

print(
    "individual_page.html"
)

print(
    "form_data.json"
)

print(
    "result_page.html"
)

print(
    "response_headers.json"
)

print(
    "response_history.json"
)

print(
    "parsed_result.json"
)

print(
    "\n===== DONE ====="
)