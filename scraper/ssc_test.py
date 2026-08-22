import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"
INDIVIDUAL_URL = BASE_URL + "individual/"

ROLL = "100001"

OUTPUT_DIR = "scraper"
os.makedirs(OUTPUT_DIR, exist_ok=True)


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


session = requests.Session()
session.headers.update(headers)


# ============================================================
# 1. OPEN SSC INDIVIDUAL RESULT PAGE
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


# Save original page
with open(
    os.path.join(OUTPUT_DIR, "individual_page.html"),
    "w",
    encoding="utf-8"
) as f:
    f.write(page.text)


if page.status_code != 200:
    raise SystemExit(
        f"Could not open individual result page. "
        f"HTTP {page.status_code}"
    )


# ============================================================
# 2. PARSE FORM
# ============================================================

soup = BeautifulSoup(page.text, "html.parser")

form = soup.find("form")

if not form:
    print("\nERROR: No <form> found on Individual Result page.")

    with open(
        os.path.join(OUTPUT_DIR, "form_error.html"),
        "w",
        encoding="utf-8"
    ) as f:
        f.write(page.text)

    raise SystemExit(1)


print("\n===== FORM FOUND =====")

form_action = form.get("action", "").strip()
form_method = form.get("method", "get").strip().lower()

print("Form method:", form_method)
print("Form action:", form_action)


# Exact absolute action URL
FORM_ACTION_URL = urljoin(page.url, form_action)

print("Resolved action:", FORM_ACTION_URL)


# ============================================================
# 3. COLLECT ALL FORM FIELDS
# ============================================================

form_data = {}


# ---------- INPUTS ----------
inputs = form.find_all("input")

print("\n===== INPUT FIELDS =====")

for inp in inputs:

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

    # Ignore submit/reset buttons for now.
    # We will add the clicked submit button below.
    if input_type in ["submit", "button", "reset", "image"]:
        continue

    # Checkbox/radio only if checked
    if input_type in ["checkbox", "radio"]:
        if not inp.has_attr("checked"):
            continue

    form_data[name] = value

    print(
        f"{name!r} = {value!r} "
        f"(type={input_type})"
    )


# ---------- SELECTS ----------
selects = form.find_all("select")

print("\n===== SELECT FIELDS =====")

for select in selects:

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
        first_option = select.find("option")

        if first_option:
            value = first_option.get(
                "value",
                first_option.get_text(strip=True)
            )
        else:
            value = ""

    form_data[name] = value

    print(
        f"{name!r} = {value!r}"
    )


# ---------- TEXTAREAS ----------
textareas = form.find_all("textarea")

print("\n===== TEXTAREA FIELDS =====")

for textarea in textareas:

    name = textarea.get("name")

    if not name:
        continue

    value = textarea.get_text()

    form_data[name] = value

    print(
        f"{name!r} = {value!r}"
    )


# ============================================================
# 4. ADD ROLL
# ============================================================

# The actual roll supplied by the scraper.
form_data["roll"] = ROLL


# ============================================================
# 5. HANDLE SUBMIT BUTTON
# ============================================================

submit_buttons = form.find_all(
    ["input", "button"]
)

submit_found = False

for button in submit_buttons:

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

        print(
            "\nSubmit button detected:",
            name,
            "=",
            value
        )

        submit_found = True
        break


# Fallback for the existing website form
if not submit_found:

    form_data["button2"] = "Submit"

    print(
        "\nNo named submit button detected."
    )

    print(
        "Using fallback:",
        "button2 = Submit"
    )


# ============================================================
# 6. SAVE COLLECTED FORM DATA
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


print("\n===== FINAL POST DATA =====")

for key, value in form_data.items():

    # Avoid printing extremely large values
    display_value = str(value)

    if len(display_value) > 500:
        display_value = (
            display_value[:500]
            + "... [TRUNCATED]"
        )

    print(
        f"{key!r}: {display_value!r}"
    )


# ============================================================
# 7. PREPARE POST HEADERS
# ============================================================

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


# ============================================================
# 8. SHOW SESSION COOKIES
# ============================================================

print("\n===== SESSION COOKIES =====")

cookies_for_log = {}

for cookie in session.cookies:

    cookies_for_log[cookie.name] = cookie.value

    print(
        cookie.name,
        "=",
        cookie.value
    )


with open(
    os.path.join(
        OUTPUT_DIR,
        "cookies.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        cookies_for_log,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 9. POST RESULT REQUEST
# ============================================================

print("\nSubmitting Roll:", ROLL)
print("POST URL:", FORM_ACTION_URL)

try:

    result = session.post(
        FORM_ACTION_URL,
        data=form_data,
        headers=post_headers,
        timeout=30,
        allow_redirects=True
    )

except requests.RequestException as e:

    print("\nPOST ERROR:")
    print(repr(e))

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
# 10. POST RESPONSE INFORMATION
# ============================================================

print("\n===== POST RESPONSE =====")

print(
    "POST Status:",
    result.status_code
)

print(
    "Final URL:",
    result.url
)

print(
    "History:",
    [
        r.status_code
        for r in result.history
    ]
)

print(
    "Result Page Size:",
    len(result.content)
)


# ============================================================
# 11. SAVE RESPONSE HEADERS
# ============================================================

response_headers = {}

for key, value in result.headers.items():

    response_headers[key] = value

    print(
        f"{key}: {value}"
    )


with open(
    os.path.join(
        OUTPUT_DIR,
        "response_headers.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        response_headers,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 12. SAVE REDIRECT HISTORY
# ============================================================

history_data = []

for response in result.history:

    history_data.append({
        "status_code": response.status_code,
        "url": response.url,
        "headers": dict(response.headers),
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
        history_data,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 13. SAVE RESULT HTML
# ============================================================

with open(
    os.path.join(
        OUTPUT_DIR,
        "result_page.html"
    ),
    "w",
    encoding="utf-8"
) as f:

    f.write(result.text)


# ============================================================
# 14. SAVE ERROR BODY
# ============================================================

if result.status_code >= 400:

    print(
        "\n===== ERROR BODY ====="
    )

    print(
        result.text[:10000]
    )

    with open(
        os.path.join(
            OUTPUT_DIR,
            "error_body.html"
        ),
        "w",
        encoding="utf-8"
    ) as f:

        f.write(result.text)

else:

    print(
        "\nPOST did not return an HTTP error."
    )


# ============================================================
# 15. RESULT PAGE TEXT
# ============================================================

print(
    "\n===== RESULT PAGE TEXT =====\n"
)

result_soup = BeautifulSoup(
    result.text,
    "html.parser"
)

text = result_soup.get_text(
    "\n",
    strip=True
)

print(
    text[:5000]
)


# ============================================================
# 16. TABLES
# ============================================================

print(
    "\n===== TABLES ====="
)

tables = result_soup.find_all(
    "table"
)

print(
    "Tables found:",
    len(tables)
)

for i, table in enumerate(
    tables,
    1
):

    print(
        f"\n--- TABLE {i} ---"
    )

    rows = table.find_all("tr")

    for row in rows:

        cells = row.find_all(
            ["th", "td"]
        )

        values = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in cells
        ]

        if values:
            print(values)


# ============================================================
# 17. FINAL STATUS
# ============================================================

print(
    "\n===== DEBUG FILES SAVED ====="
)

print(
    "scraper/individual_page.html"
)

print(
    "scraper/form_data.json"
)

print(
    "scraper/cookies.json"
)

print(
    "scraper/result_page.html"
)

print(
    "scraper/response_headers.json"
)

print(
    "scraper/response_history.json"
)

if result.status_code >= 400:

    print(
        "scraper/error_body.html"
    )

print(
    "\n===== DONE ====="
)