import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

MASTER_URL = (
    "https://esifssc.bise-ctg.gov.bd/"
    "esif_accounts.php"
)

SSC_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/"
    "individual/"
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
}


# ============================================================
# DIRECTORY
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
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
# CLEAN
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


# ============================================================
# NUMBER
# ============================================================

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
        number_value = float(
            match.group()
        )

        if number_value.is_integer():
            return int(number_value)

        return number_value

    except Exception:
        return None


# ============================================================
# DOWNLOAD MASTER
# ============================================================

def get_master():

    print(
        "=" * 70
    )

    print(
        "STEP 1: DOWNLOADING INSTITUTION MASTER LIST"
    )

    print(
        "URL:",
        MASTER_URL
    )

    print(
        "=" * 70
    )

    response = session.get(
        MASTER_URL,
        timeout=TIMEOUT
    )

    print(
        "HTTP Status:",
        response.status_code
    )

    response.raise_for_status()

    response.encoding = (
        response.apparent_encoding
        or response.encoding
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    tables = soup.find_all(
        "table"
    )

    print(
        "Tables found:",
        len(tables)
    )

    institution_table = None

    for table in tables:

        text = clean_text(
            table.get_text(
                " ",
                strip=True
            )
        ).upper()

        if (
            "EIIN" in text
            and
            "INSTITUTE NAME" in text
        ):

            institution_table = table
            break

    if institution_table is None:

        raise RuntimeError(
            "Institution table not found."
        )

    institutions = []

    for row in institution_table.find_all("tr"):

        cells = row.find_all(
            ["td", "th"]
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

        eiin = ""

        name = ""

        total_students = 0

        # Normal table:
        # SL | EIIN | NAME | STUDENTS

        if len(values) >= 4:

            if values[1].isdigit():

                eiin = values[1]

                name = values[2]

                total_students = (
                    number(values[3])
                    or 0
                )

        # Fallback:
        # EIIN | NAME | STUDENTS

        if not eiin:

            if values[0].isdigit():

                eiin = values[0]

                name = values[1]

                if len(values) >= 3:

                    total_students = (
                        number(values[2])
                        or 0
                    )

        if not eiin:
            continue

        if not name:
            continue

        institutions.append({

            "eiin":
                eiin,

            "institution_name":
                name,

            "total_students":
                total_students,

        })

    # Remove duplicates

    unique = {}

    for item in institutions:

        unique[
            item["eiin"]
        ] = item

    institutions = list(
        unique.values()
    )

    print(
        "Institutions found:",
        len(institutions)
    )

    return institutions


# ============================================================
# OPEN SSC FORM
# ============================================================

def open_ssc_form():

    print()
    print(
        "=" * 70
    )

    print(
        "STEP 2: OPENING SSC RESULT FORM"
    )

    print(
        "=" * 70
    )

    response = session.get(
        SSC_URL,
        timeout=TIMEOUT
    )

    print(
        "HTTP Status:",
        response.status_code
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    form = soup.find(
        "form"
    )

    if not form:

        raise RuntimeError(
            "SSC result form not found."
        )

    action = form.get(
        "action",
        ""
    )

    method = form.get(
        "method",
        "post"
    ).lower()

    from urllib.parse import urljoin

    action_url = urljoin(
        response.url,
        action
    )

    base_data = {}

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

        if input_type in (
            "submit",
            "button",
            "reset",
            "image"
        ):
            continue

        base_data[name] = inp.get(
            "value",
            ""
        )

    print(
        "Result URL:",
        action_url
    )

    print(
        "Form method:",
        method
    )

    print(
        "Base form fields:",
        base_data
    )

    return (
        action_url,
        method,
        base_data,
        response.url
    )


# ============================================================
# PARSE INSTITUTION RESULT
# ============================================================

def parse_institution_result(
    html,
    institution
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    result = {

        "eiin":
            institution["eiin"],

        "institution_name":
            institution[
                "institution_name"
            ],

        "district":
            "",

        "thana":
            "",

        "appeared":
            institution[
                "total_students"
            ],

        "passed":
            0,

        "passing_rate":
            0,

        "gpa5":
            0,

        "total_gpa":
            0,

        "year":
            YEAR,

        "board":
            BOARD,

    }

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    upper = page_text.upper()

    # ========================================================
    # SHOW TABLE STRUCTURE
    # ========================================================

    print()
    print(
        "RESULT PAGE TABLES:",
        len(
            soup.find_all("table")
        )
    )

    for table_index, table in enumerate(
        soup.find_all("table")
    ):

        rows = table.find_all("tr")

        print()
        print(
            f"TABLE #{table_index + 1}"
        )

        for row in rows[:5]:

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

            if values:

                print(
                    values
                )

    # ========================================================
    # TEXT BASED EXTRACTION
    # ========================================================

    patterns = {

        "appeared": [
            r"TOTAL\s*(?:CANDIDATE|STUDENT|EXAMINEE).*?(\d+)",
            r"APPEARED.*?(\d+)",
        ],

        "passed": [
            r"TOTAL\s*PASSED.*?(\d+)",
            r"PASSED.*?(\d+)",
        ],

        "gpa5": [
            r"GPA\s*5.*?(\d+)",
            r"GPA5.*?(\d+)",
            r"5\.00.*?(\d+)",
        ],

        "passing_rate": [
            r"PASSING\s*RATE.*?([0-9]+(?:\.[0-9]+)?)",
            r"PASS\s*RATE.*?([0-9]+(?:\.[0-9]+)?)",
        ],

    }

    for field, field_patterns in patterns.items():

        for pattern in field_patterns:

            match = re.search(
                pattern,
                upper
            )

            if match:

                value = number(
                    match.group(1)
                )

                if value is not None:

                    result[field] = value

                    break

    # ========================================================
    # DISTRICT
    # ========================================================

    district_patterns = [

        r"DISTRICT\s*[:\-]\s*([A-Z .']+)",

        r"DISTRICT\s+([A-Z .']+)",

    ]

    for pattern in district_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:

                result["district"] = (
                    value.title()
                )

                break

    # ========================================================
    # THANA
    # ========================================================

    thana_patterns = [

        r"THANA\s*[:\-]\s*([A-Z .']+)",

        r"UPAZILA\s*[:\-]\s*([A-Z .']+)",

        r"THANA\s+([A-Z .']+)",

    ]

    for pattern in thana_patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:

                result["thana"] = (
                    value.title()
                )

                break

    # ========================================================
    # PASSING RATE CALCULATION
    # ========================================================

    appeared = number(
        result["appeared"]
    )

    passed = number(
        result["passed"]
    )

    if (
        appeared
        and
        appeared > 0
        and
        passed is not None
    ):

        result["passing_rate"] = round(
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

    print()
    print(
        "=" * 70
    )

    print(
        "SSC 2026 INSTITUTION COLLECTION"
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

    # --------------------------------------------------------
    # MASTER
    # --------------------------------------------------------

    institutions = get_master()

    if TEST_MODE:

        institutions = [

            item
            for item in institutions

            if item["eiin"] ==
            TEST_EIIN

        ]

    if not institutions:

        raise RuntimeError(
            "No institution selected."
        )

    # --------------------------------------------------------
    # SSC FORM
    # --------------------------------------------------------

    (
        action_url,
        method,
        base_data,
        referer
    ) = open_ssc_form()

    results = []

    failed = []

    # --------------------------------------------------------
    # COLLECTION
    # --------------------------------------------------------

    total = len(
        institutions
    )

    for index, institution in enumerate(
        institutions,
        start=1
    ):

        print()
        print(
            "-" * 70
        )

        print(
            f"[{index}/{total}]"
        )

        print(
            "EIIN:",
            institution["eiin"]
        )

        print(
            "Institution:",
            institution[
                "institution_name"
            ]
        )

        # ----------------------------------------------------
        # REQUEST
        # ----------------------------------------------------

        data = dict(
            base_data
        )

        # IMPORTANT:
        # Institution-wise SSC page uses EIIN.

        data["eiin"] = (
            institution["eiin"]
        )

        # Keep roll empty if the form
        # contains it.

        if "roll" in data:

            data["roll"] = ""

        print(
            "REQUEST START:",
            institution["eiin"]
        )

        try:

            if method == "get":

                response = session.get(
                    action_url,
                    params=data,
                    headers={
                        "Referer":
                            referer
                    },
                    timeout=TIMEOUT
                )

            else:

                response = session.post(
                    action_url,
                    data=data,
                    headers={
                        "Referer":
                            referer,
                        "Origin":
                            "https://sresult.bise-ctg.gov.bd",
                    },
                    timeout=TIMEOUT
                )

        except Exception as error:

            print(
                "REQUEST ERROR:",
                error
            )

            failed.append({

                "eiin":
                    institution["eiin"],

                "institution_name":
                    institution[
                        "institution_name"
                    ],

                "error":
                    str(error)

            })

            continue

        print(
            "REQUEST DONE:",
            institution["eiin"],
            "| HTTP",
            response.status_code
        )

        # ----------------------------------------------------
        # HTTP
        # ----------------------------------------------------

        if response.status_code >= 400:

            failed.append({

                "eiin":
                    institution["eiin"],

                "institution_name":
                    institution[
                        "institution_name"
                    ],

                "error":
                    f"HTTP {response.status_code}"

            })

            continue

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        print(
            "PARSING RESULT..."
        )

        try:

            result = parse_institution_result(
                response.text,
                institution
            )

        except Exception as error:

            print(
                "PARSING ERROR:",
                error
            )

            failed.append({

                "eiin":
                    institution["eiin"],

                "institution_name":
                    institution[
                        "institution_name"
                    ],

                "error":
                    str(error)

            })

            continue

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        print()
        print(
            "PARSED INSTITUTION DATA:"
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        results.append(
            result
        )

        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
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
            failed,
            file,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    elapsed = round(
        time.time() - start,
        2
    )

    print()
    print(
        "=" * 70
    )

    print(
        "INSTITUTION TEST COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "Institutions processed:",
        len(institutions)
    )

    print(
        "Successful:",
        len(results)
    )

    print(
        "Failed:",
        len(failed)
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