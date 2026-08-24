import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from pathlib import Path


# ============================================================
# SSC 2026 INSTITUTION COLLECTOR
# ============================================================

YEAR = 2026
BOARD = "Chattogram Board"

MASTER_URL = (
    "https://esifssc.bise-ctg.gov.bd/"
    "esif_accounts.php"
)

SSC_BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/"
)

SSC_INDIVIDUAL_URL = (
    SSC_BASE_URL +
    "individual/"
)

SSC_RESULT_URL = (
    SSC_INDIVIDUAL_URL +
    "result.php"
)


# ============================================================
# FILES
# ============================================================

OUTPUT_DIR = Path("institution-collector")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "institution_results.json"
)

MASTER_FILE = (
    OUTPUT_DIR /
    "institutions.json"
)

FAILED_FILE = (
    OUTPUT_DIR /
    "failed_institutions.json"
)


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = (
    5,
    20
)

MIN_DELAY = 0.10
MAX_DELAY = 0.20

SAVE_EVERY = 50

# ------------------------------------------------------------
# TEST MODE
# ------------------------------------------------------------
# প্রথমে True রাখো।
# তাহলে শুধু TEST_EIIN নিয়ে কাজ করবে।
#
# সব institution চালাতে:
# TEST_MODE = False
# ------------------------------------------------------------

TEST_MODE = True

TEST_EIIN = "103086"


# ============================================================
# HEADERS
# ============================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0.0.0 "
        "Mobile Safari/537.36"
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


def to_int(value):

    value = clean_text(
        value
    )

    value = value.replace(
        ",",
        ""
    )

    match = re.search(
        r"\d+",
        value
    )

    if not match:
        return 0

    try:
        return int(
            match.group()
        )
    except Exception:
        return 0


def to_float(value):

    value = clean_text(
        value
    )

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
        return float(
            match.group()
        )
    except Exception:
        return None


def save_json(path, data):

    temp_path = Path(
        str(path) +
        ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_path.replace(
        path
    )


# ============================================================
# MASTER LIST
# ============================================================

def download_master_page():

    print(
        "=" * 70,
        flush=True
    )

    print(
        "STEP 1: DOWNLOADING INSTITUTION MASTER LIST",
        flush=True
    )

    print(
        "URL:",
        MASTER_URL,
        flush=True
    )

    response = session.get(
        MASTER_URL,
        timeout=REQUEST_TIMEOUT
    )

    print(
        "HTTP Status:",
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    response.encoding = (
        response.apparent_encoding
    )

    return response.text


# ============================================================
# FIND MASTER TABLE
# ============================================================

def find_master_table(soup):

    tables = soup.find_all(
        "table"
    )

    print(
        "Tables found:",
        len(tables),
        flush=True
    )

    for table in tables:

        first_row = table.find(
            "tr"
        )

        if not first_row:
            continue

        headers = [

            clean_text(
                cell.get_text(
                    " ",
                    strip=True
                )
            ).lower()

            for cell in first_row.find_all(
                ["th", "td"]
            )
        ]

        text = " ".join(
            headers
        )

        if (
            "eiin" in text
            and (
                "institute" in text
                or "institution" in text
            )
        ):

            return table

    return None


# ============================================================
# PARSE MASTER DATA
# ============================================================

def parse_master_data(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    table = find_master_table(
        soup
    )

    if table is None:

        raise RuntimeError(
            "Institution master table not found."
        )

    rows = table.find_all(
        "tr"
    )

    institutions = []

    for row in rows:

        cells = row.find_all(
            ["td", "th"]
        )

        if len(cells) < 3:
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

        # ----------------------------------------------------
        # Find EIIN position dynamically
        # ----------------------------------------------------

        eiin_index = None

        for i, value in enumerate(
            values
        ):

            if re.fullmatch(
                r"\d{5,7}",
                value
            ):

                eiin_index = i

                break

        if eiin_index is None:
            continue

        eiin = values[
            eiin_index
        ]

        # ----------------------------------------------------
        # Institution name
        # ----------------------------------------------------

        name_index = (
            eiin_index + 1
        )

        if (
            name_index >=
            len(values)
        ):

            continue

        institution_name = clean_text(
            values[name_index]
        )

        if not institution_name:
            continue

        # ----------------------------------------------------
        # First numeric value after name
        # is normally total students.
        # ----------------------------------------------------

        total_students = 0

        for value in values[
            name_index + 1:
        ]:

            number = to_int(
                value
            )

            if number > 0:

                total_students = number

                break

        institutions.append({

            "eiin":
                eiin,

            "institution_name":
                institution_name,

            "total_students":
                total_students,

            "year":
                YEAR,

            "board":
                BOARD,

        })

    # --------------------------------------------------------
    # Remove duplicate EIIN
    # --------------------------------------------------------

    unique = {}

    for item in institutions:

        unique[
            item["eiin"]
        ] = item

    institutions = list(
        unique.values()
    )

    institutions.sort(
        key=lambda x:
            x["eiin"]
    )

    return institutions


# ============================================================
# SAVE MASTER
# ============================================================

def save_master(
    institutions
):

    data = {

        "metadata": {

            "year":
                YEAR,

            "board":
                BOARD,

            "total_institutions":
                len(institutions),

            "source":
                MASTER_URL,

        },

        "institutions":
            institutions

    }

    save_json(
        MASTER_FILE,
        data
    )


# ============================================================
# SSC PAGE
# ============================================================

def open_ssc_page():

    print(
        "=" * 70,
        flush=True
    )

    print(
        "STEP 2: OPENING SSC RESULT FORM",
        flush=True
    )

    response = session.get(
        SSC_INDIVIDUAL_URL,
        timeout=REQUEST_TIMEOUT
    )

    print(
        "HTTP Status:",
        response.status_code,
        flush=True
    )

    response.raise_for_status()

    response.encoding = (
        response.apparent_encoding
    )

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

    action = clean_text(
        form.get(
            "action",
            ""
        )
    )

    if not action:

        action = "result.php"

    if action.startswith(
        "http"
    ):

        result_url = action

    else:

        result_url = (
            SSC_INDIVIDUAL_URL +
            action
        )

    print(
        "Result URL:",
        result_url,
        flush=True
    )

    return (
        soup,
        form,
        result_url
    )


# ============================================================
# FORM DATA
# ============================================================

def get_base_form_data(
    form
):

    data = {}

    for element in form.find_all(
        "input"
    ):

        name = element.get(
            "name"
        )

        if not name:
            continue

        input_type = element.get(
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

            if not element.has_attr(
                "checked"
            ):

                continue

        data[name] = element.get(
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

        option = select.find(
            "option",
            selected=True
        )

        if option is None:

            option = select.find(
                "option"
            )

        if option:

            data[name] = option.get(
                "value",
                clean_text(
                    option.get_text()
                )
            )

    return data


# ============================================================
# GPA PARSER
# ============================================================

def parse_gpa(text):

    text = clean_text(
        text
    )

    patterns = [

        r"GPA\s*[:=]\s*([0-5](?:\.\d+)?)",

        r"RESULT\s*[:=]\s*([0-5](?:\.\d+)?)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            return to_float(
                match.group(1)
            )

    return None


# ============================================================
# TOTAL SCORE
# ============================================================

def parse_total_score(
    soup
):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    patterns = [

        r"TOTAL\s*SCORE\s*[:=]?\s*(\d+)",

        r"TOTAL\s*MARKS\s*[:=]?\s*(\d+)",

        r"TOTAL\s*[:=]\s*(\d+)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            return to_int(
                match.group(1)
            )

    return None


# ============================================================
# SUBJECT MARKS
# ============================================================

def parse_subjects(
    soup
):

    subjects = []

    seen = set()

    for table in soup.find_all(
        "table"
    ):

        for row in table.find_all(
            "tr"
        ):

            cells = row.find_all(
                ["td", "th"]
            )

            values = [

                clean_text(
                    c.get_text(
                        " ",
                        strip=True
                    )
                )

                for c in cells
            ]

            if len(values) < 3:
                continue

            if not values[0].isdigit():
                continue

            code = values[0]

            subject = values[1]

            mark = None

            match = re.search(
                r"\b(\d{1,3})\b",
                values[2]
            )

            if match:

                try:

                    mark = int(
                        match.group(1)
                    )

                except Exception:

                    pass

            key = (
                code,
                subject
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            subjects.append({

                "code":
                    code,

                "subject":
                    subject,

                "mark":
                    mark,

            })

    return subjects


# ============================================================
# PARSE STUDENT RESULT
# ============================================================

def parse_student_result(
    html,
    requested_roll
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

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    name = ""

    match = re.search(
        r"NAME\s*[:\-]?\s*([A-Z .'-]+)",
        upper
    )

    if match:

        name = clean_text(
            match.group(1)
        )

    # --------------------------------------------------------
    # INSTITUTE
    # --------------------------------------------------------

    institute = ""

    patterns = [

        r"INSTITUTE\s*[:\-]\s*(.*?)(?=\s+(?:DISTRICT|GPA|RESULT|ROLL|GROUP)\b)",

        r"INSTITUTION\s*[:\-]\s*(.*?)(?=\s+(?:DISTRICT|GPA|RESULT|ROLL|GROUP)\b)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            upper
        )

        if match:

            institute = clean_text(
                match.group(1)
            )

            break

    # --------------------------------------------------------
    # DISTRICT
    # --------------------------------------------------------

    district = ""

    match = re.search(
        r"DISTRICT\s*[:\-]\s*([A-Z .'-]+)",
        upper
    )

    if match:

        district = clean_text(
            match.group(1)
        )

    # --------------------------------------------------------
    # GPA
    # --------------------------------------------------------

    gpa = parse_gpa(
        text
    )

    # --------------------------------------------------------
    # TOTAL SCORE
    # --------------------------------------------------------

    total_score = parse_total_score(
        soup
    )

    # --------------------------------------------------------
    # SUBJECTS
    # --------------------------------------------------------

    subjects = parse_subjects(
        soup
    )

    return {

        "roll":
            str(requested_roll),

        "name":
            name,

        "institute":
            institute,

        "district":
            district,

        "gpa":
            gpa,

        "total_score":
            total_score,

        "subjects":
            subjects,

    }


# ============================================================
# GET INSTITUTION RESULT
# ============================================================

def collect_institution(
    institution,
    base_form_data,
    result_url
):

    eiin = str(
        institution["eiin"]
    )

    print()
    print(
        "-" * 70,
        flush=True
    )

    print(
        "EIIN:",
        eiin,
        flush=True
    )

    print(
        "Institution:",
        institution[
            "institution_name"
        ],
        flush=True
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # The institution master page gives institution-level
    # aggregate information.
    #
    # The SSC individual endpoint requires ROLL, not EIIN.
    #
    # Therefore this function currently performs the
    # institution lookup and preserves the master data.
    # --------------------------------------------------------

    result = dict(
        institution
    )

    result.update({

        "district":
            "",

        "thana":
            "",

        "appeared":
            institution.get(
                "total_students",
                0
            ),

        "passed":
            0,

        "passing_rate":
            0,

        "gpa5":
            0,

        "total_gpa":
            0,

    })

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = time.time()

    print()
    print(
        "=" * 70
    )

    print(
        "SSC 2026 INSTITUTION COLLECTION"
    )

    print(
        "=" * 70
    )

    print(
        "TEST MODE:",
        TEST_MODE
    )

    if TEST_MODE:

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
    # MASTER DATA
    # ========================================================

    try:

        html = download_master_page()

        institutions = parse_master_data(
            html
        )

    except Exception as error:

        print()
        print(
            "MASTER COLLECTION ERROR:",
            error
        )

        return


    print()
    print(
        "Institutions found:",
        len(institutions)
    )


    if not institutions:

        print(
            "No institutions found."
        )

        return


    save_master(
        institutions
    )


    # ========================================================
    # TEST FILTER
    # ========================================================

    if TEST_MODE:

        selected = [

            item

            for item in institutions

            if str(
                item["eiin"]
            ) == str(
                TEST_EIIN
            )

        ]

        if not selected:

            print(
                "TEST EIIN not found:",
                TEST_EIIN
            )

            return

        institutions = selected


    # ========================================================
    # SSC FORM
    # ========================================================

    try:

        (
            soup,
            form,
            result_url
        ) = open_ssc_page()

        base_form_data = (
            get_base_form_data(
                form
            )
        )

    except Exception as error:

        print()
        print(
            "SSC FORM ERROR:",
            error
        )

        return


    print()
    print(
        "Base form fields:",
        base_form_data
    )


    # ========================================================
    # COLLECTION
    # ========================================================

    results = []

    failed = []


    for index, institution in enumerate(
        institutions,
        start=1
    ):

        print()
        print(
            f"[{index}/{len(institutions)}]"
        )

        try:

            result = collect_institution(

                institution,

                base_form_data,

                result_url

            )

            results.append(
                result
            )

        except Exception as error:

            print(
                "ERROR:",
                error
            )

            failed.append({

                "eiin":
                    institution[
                        "eiin"
                    ],

                "institution_name":
                    institution[
                        "institution_name"
                    ],

                "error":
                    str(error)

            })


        # ----------------------------------------------------
        # CHECKPOINT
        # ----------------------------------------------------

        if (
            len(results) %
            SAVE_EVERY == 0
            and results
        ):

            save_json(
                OUTPUT_FILE,
                {
                    "metadata": {

                        "year":
                            YEAR,

                        "board":
                            BOARD,

                        "total":
                            len(results),

                    },

                    "institutions":
                        results
                }
            )

            save_json(
                FAILED_FILE,
                failed
            )

            print(
                "Checkpoint saved."
            )


        time.sleep(
            random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )
        )


    # ========================================================
    # FINAL SAVE
    # ========================================================

    final_data = {

        "metadata": {

            "year":
                YEAR,

            "board":
                BOARD,

            "total_institutions":
                len(results),

            "source":
                MASTER_URL,

            "created":
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

        },

        "institutions":
            results

    }


    save_json(
        OUTPUT_FILE,
        final_data
    )

    save_json(
        FAILED_FILE,
        failed
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    elapsed = round(
        time.time() -
        start_time,
        2
    )

    print()
    print(
        "=" * 70
    )

    print(
        "INSTITUTION COLLECTION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "Institutions collected:",
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