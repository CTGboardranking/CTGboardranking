import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from pathlib import Path
from urllib.parse import urljoin


# ============================================================
# CONFIG
# ============================================================

SOURCE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/index.php"
)

OUTPUT_FILE = Path(
    "institution-collector/institution_results.json"
)

FAILED_FILE = Path(
    "institution-collector/failed_institutions.json"
)

TEST_MODE = True

TEST_EIIN = "103086"

MIN_DELAY = 0.1

MAX_DELAY = 0.2

TIMEOUT = (5, 20)

YEAR = 2026

BOARD = "Chattogram Board"


# ============================================================
# HEADERS
# ============================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
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
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# DIRECTORY
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace(
        "\xa0",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def number(value):

    value = clean_text(value)

    value = value.replace(
        ",",
        ""
    )

    match = re.search(
        r"\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:

        value = float(
            match.group()
        )

        if value.is_integer():

            return int(value)

        return value

    except Exception:

        return None


# ============================================================
# OPEN INSTITUTE RESULT PAGE
# ============================================================

def open_page():

    print(
        "=" * 70
    )

    print(
        "STEP 1: OPENING INSTITUTE RESULT PAGE"
    )

    print(
        "URL:",
        SOURCE_URL
    )

    print(
        "=" * 70
    )

    response = session.get(
        SOURCE_URL,
        timeout=TIMEOUT
    )

    print(
        "HTTP Status:",
        response.status_code
    )

    print(
        "Final URL:",
        response.url
    )

    response.raise_for_status()

    response.encoding = (
        response.apparent_encoding
        or response.encoding
    )

    return response


# ============================================================
# INSPECT FORM
# ============================================================

def inspect_form(response):

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    forms = soup.find_all(
        "form"
    )

    print()
    print(
        "Forms found:",
        len(forms)
    )

    if not forms:

        raise RuntimeError(
            "No form found on index.php"
        )

    for index, form in enumerate(
        forms,
        start=1
    ):

        print()
        print(
            "-" * 70
        )

        print(
            f"FORM #{index}"
        )

        print(
            "Action:",
            form.get(
                "action",
                ""
            )
        )

        print(
            "Method:",
            form.get(
                "method",
                "get"
            )
        )

        print(
            "INPUT FIELDS:"
        )

        for inp in form.find_all(
            "input"
        ):

            print({

                "name":
                    inp.get("name"),

                "type":
                    inp.get(
                        "type",
                        "text"
                    ),

                "value":
                    inp.get(
                        "value",
                        ""
                    ),

                "placeholder":
                    inp.get(
                        "placeholder",
                        ""
                    )

            })

        print(
            "SELECT FIELDS:"
        )

        for select in form.find_all(
            "select"
        ):

            print({

                "name":
                    select.get("name"),

                "options":
                    [
                        clean_text(
                            option.get(
                                "value",
                                ""
                            )
                        )
                        for option
                        in select.find_all(
                            "option"
                        )
                    ]

            })

    return soup, forms[0]


# ============================================================
# BUILD FORM DATA
# ============================================================

def build_form_data(
    form,
    eiin
):

    data = {}

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

        if input_type in (
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

        data[name] = inp.get(
            "value",
            ""
        )

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

            data[name] = selected.get(
                "value",
                clean_text(
                    selected.get_text()
                )
            )

    # ========================================================
    # FIND EIIN FIELD
    # ========================================================

    eiin_field = None

    possible_names = [

        "eiin",
        "EIIN",
        "institute",
        "institute_eiin",
        "institute_eiin_no",
        "institute_no",
        "institute_id",

    ]

    for name in possible_names:

        if name in data:

            eiin_field = name

            break

    # If not found, inspect input names

    if eiin_field is None:

        for inp in form.find_all(
            "input"
        ):

            name = inp.get(
                "name"
            )

            placeholder = clean_text(
                inp.get(
                    "placeholder",
                    ""
                )
            ).lower()

            if not name:
                continue

            combined = (
                name.lower()
                + " "
                + placeholder
            )

            if (
                "eiin" in combined
                or
                "institute" in combined
            ):

                eiin_field = name

                break

    if eiin_field is None:

        raise RuntimeError(
            "Could not identify EIIN input field."
        )

    data[eiin_field] = str(
        eiin
    )

    print()
    print(
        "EIIN field detected:",
        eiin_field
    )

    print(
        "POST data:",
        data
    )

    return data


# ============================================================
# PARSE INSTITUTION RESULT
# ============================================================

def parse_result(
    html,
    eiin
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    upper = text.upper()

    print()
    print(
        "=" * 70
    )

    print(
        "STEP 3: PARSING INSTITUTION RESULT"
    )

    print(
        "=" * 70
    )

    print(
        "Tables found:",
        len(
            soup.find_all("table")
        )
    )

    # ========================================================
    # PRINT TABLES
    # ========================================================

    for table_index, table in enumerate(
        soup.find_all("table"),
        start=1
    ):

        print()
        print(
            f"TABLE #{table_index}"
        )

        for row in table.find_all("tr"):

            values = [

                clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )

                for cell
                in row.find_all(
                    ["th", "td"]
                )

            ]

            if values:

                print(
                    values
                )

    # ========================================================
    # DEFAULT
    # ========================================================

    result = {

        "eiin":
            str(eiin),

        "institution_name":
            "",

        "district":
            "",

        "thana":
            "",

        "appeared":
            None,

        "passed":
            None,

        "passing_rate":
            None,

        "gpa5":
            None,

        "total_gpa":
            None,

        "year":
            YEAR,

        "board":
            BOARD,

    }

    # ========================================================
    # INSTITUTE NAME
    # ========================================================

    patterns = [

        r"INSTITUTE\s+NAME\s*:\s*(.+?)\s*\(\s*"
        + re.escape(str(eiin))
        + r"\s*\)",

        r"INSTITUTE\s+NAME\s*:\s*(.+)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            name = clean_text(
                match.group(1)
            )

            name = re.sub(
                r"\s*\(\s*"
                + re.escape(str(eiin))
                + r"\s*\)",
                "",
                name,
                flags=re.I
            )

            result[
                "institution_name"
            ] = name.title()

            break

    # ========================================================
    # DISTRICT
    # ========================================================

    district_patterns = [

        r"ZILLA\s*:\s*"
        r"(.+?)\s*\(\s*\d+\s*\)",

        r"DISTRICT\s*:\s*"
        r"(.+?)\s*\(\s*\d+\s*\)",

    ]

    for pattern in district_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            result[
                "district"
            ] = clean_text(
                match.group(1)
            ).title()

            break

    # ========================================================
    # THANA
    # ========================================================

    thana_patterns = [

        r"THANA\s*:\s*"
        r"(.+?)\s*\(\s*\d+\s*\)",

        r"UPAZILA\s*:\s*"
        r"(.+?)\s*\(\s*\d+\s*\)",

    ]

    for pattern in thana_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            result[
                "thana"
            ] = clean_text(
                match.group(1)
            ).title()

            break

    # ========================================================
    # APP
    # ========================================================

    app_patterns = [

        r"\bAPP\s*:\s*(\d+)",

        r"APPEARED\s*:\s*(\d+)",

    ]

    for pattern in app_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            result[
                "appeared"
            ] = int(
                match.group(1)
            )

            break

    # ========================================================
    # PASS
    # ========================================================

    pass_patterns = [

        r"\bPASS\s*:\s*(\d+)",

        r"PASSED\s*:\s*(\d+)",

    ]

    for pattern in pass_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            result[
                "passed"
            ] = int(
                match.group(1)
            )

            break

    # ========================================================
    # PERCENT
    # ========================================================

    percent_patterns = [

        r"PERCENT\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*%",

        r"PASS(?:ING)?\s*RATE\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*%",

    ]

    for pattern in percent_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            result[
                "passing_rate"
            ] = float(
                match.group(1)
            )

            break

    # ========================================================
    # GPA5
    # ========================================================

    gpa5_patterns = [

        r"GPA\s*5\s*:\s*(\d+)",

        r"GPA5\s*:\s*(\d+)",

    ]

    for pattern in gpa5_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            result[
                "gpa5"
            ] = int(
                match.group(1)
            )

            break

    # ========================================================
    # PASSING RATE FALLBACK
    # ========================================================

    if (
        result["passing_rate"]
        is None
    ):

        appeared = result[
            "appeared"
        ]

        passed = result[
            "passed"
        ]

        if (
            appeared
            and
            appeared > 0
            and
            passed is not None
        ):

            result[
                "passing_rate"
            ] = round(
                passed /
                appeared *
                100,
                2
            )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    start = time.time()

    print(
        "=" * 70
    )

    print(
        "SSC 2026 INSTITUTION TEST"
    )

    print(
        "TEST MODE:",
        TEST_MODE
    )

    print(
        "TEST EIIN:",
        TEST_EIIN
    )

    print(
        "MIN_DELAY:",
        MIN_DELAY
    )

    print(
        "MAX_DELAY:",
        MAX_DELAY
    )

    print(
        "=" * 70
    )

    # ========================================================
    # OPEN PAGE
    # ========================================================

    response = open_page()

    # ========================================================
    # INSPECT FORM
    # ========================================================

    soup, form = inspect_form(
        response
    )

    # ========================================================
    # ACTION URL
    # ========================================================

    action = form.get(
        "action",
        ""
    )

    action_url = urljoin(
        response.url,
        action
    )

    method = form.get(
        "method",
        "get"
    ).lower()

    print()
    print(
        "FORM ACTION:",
        action_url
    )

    print(
        "FORM METHOD:",
        method
    )

    # ========================================================
    # FORM DATA
    # ========================================================

    form_data = build_form_data(
        form,
        TEST_EIIN
    )

    # ========================================================
    # REQUEST
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "STEP 2: SUBMITTING EIIN"
    )

    print(
        "=" * 70
    )

    print(
        "EIIN:",
        TEST_EIIN
    )

    print(
        "Request URL:",
        action_url
    )

    try:

        if method == "get":

            result_response = (
                session.get(
                    action_url,
                    params=form_data,
                    headers={
                        "Referer":
                            response.url
                    },
                    timeout=TIMEOUT
                )
            )

        else:

            result_response = (
                session.post(
                    action_url,
                    data=form_data,
                    headers={

                        "Referer":
                            response.url,

                        "Origin":
                            "https://sresult.bise-ctg.gov.bd",

                    },
                    timeout=TIMEOUT
                )
            )

    except Exception as error:

        print(
            "REQUEST ERROR:",
            error
        )

        raise SystemExit(1)

    print(
        "HTTP Status:",
        result_response.status_code
    )

    print(
        "Final URL:",
        result_response.url
    )

    print(
        "Response size:",
        len(
            result_response.text
        ),
        "bytes"
    )

    if result_response.status_code >= 400:

        raise SystemExit(
            f"HTTP ERROR: "
            f"{result_response.status_code}"
        )

    # ========================================================
    # PARSE
    # ========================================================

    result = parse_result(
        result_response.text,
        TEST_EIIN
    )

    # ========================================================
    # SHOW RESULT
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "INSTITUTION TEST RESULT"
    )

    print(
        "=" * 70
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

    # ========================================================
    # SAVE TEST RESULT
    # ========================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            [result],
            file,
            ensure_ascii=False,
            indent=2
        )

    with open(
        FAILED_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            [],
            file,
            ensure_ascii=False,
            indent=2
        )

    elapsed = round(
        time.time() - start,
        2
    )

    print()
    print(
        "=" * 70
    )

    print(
        "TEST COMPLETED"
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print(
        "Failed file:",
        FAILED_FILE
    )

    print(
        "Time:",
        elapsed,
        "seconds"
    )

    print(
        "=" * 70
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()