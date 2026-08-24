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

INDEX_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/index.php"
)

MASTER_URL = (
    "https://esifssc.bise-ctg.gov.bd/"
    "esif_accounts.php"
)

OUTPUT_FILE = Path(
    "institution-collector/institution_results.json"
)

FAILED_FILE = Path(
    "institution-collector/failed_institutions.json"
)

# ------------------------------------------------------------
# FULL COLLECTION
# ------------------------------------------------------------

TEST_MODE = False

TEST_EIIN = "103086"

EXPECTED_INSTITUTIONS = 1293

# ------------------------------------------------------------
# SPEED
# ------------------------------------------------------------

MIN_DELAY = 0.05
MAX_DELAY = 0.3

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
# DOWNLOAD MASTER INSTITUTION LIST
# ============================================================

def download_master_list():

    print()
    print("=" * 70)
    print("STEP 1: DOWNLOADING INSTITUTION MASTER LIST")
    print("=" * 70)

    print(
        "URL:",
        MASTER_URL
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

    institutions = []

    for table in tables:

        rows = table.find_all(
            "tr"
        )

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

            if len(values) < 3:
                continue

            # ------------------------------------------------
            # Expected:
            #
            # 0 = SL
            # 1 = EIIN
            # 2 = INSTITUTE NAME
            # 3 = TOTAL STUDENTS
            # ------------------------------------------------

            eiin = ""
            institution_name = ""

            if len(values) >= 4:

                possible_eiin = values[1]

                if possible_eiin.isdigit():

                    eiin = possible_eiin

                    institution_name = values[2]

            if not eiin:

                if values[0].isdigit():

                    eiin = values[0]

                    institution_name = values[1]

            if not eiin:
                continue

            if not institution_name:
                continue

            # Header skip

            if (
                "eiin"
                in institution_name.lower()
            ):

                continue

            institutions.append({

                "eiin":
                    str(eiin),

                "institution_name":
                    institution_name,

            })

        # Usually first valid institution table is enough

        if institutions:
            break

    # --------------------------------------------------------
    # Remove duplicates
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
            int(x["eiin"])
    )

    print(
        "Institutions found:",
        len(institutions)
    )

    if EXPECTED_INSTITUTIONS:

        if len(institutions) != EXPECTED_INSTITUTIONS:

            print()
            print(
                "WARNING:"
            )

            print(
                "Expected:",
                EXPECTED_INSTITUTIONS
            )

            print(
                "Found:",
                len(institutions)
            )

    return institutions


# ============================================================
# OPEN RESULT FORM
# ============================================================

def open_result_form():

    print()
    print("=" * 70)
    print("STEP 2: OPENING SSC INSTITUTION RESULT FORM")
    print("=" * 70)

    response = session.get(
        INDEX_URL,
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

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    forms = soup.find_all(
        "form"
    )

    print(
        "Forms found:",
        len(forms)
    )

    if not forms:

        raise RuntimeError(
            "No form found."
        )

    selected_form = None

    for form in forms:

        for inp in form.find_all(
            "input"
        ):

            name = inp.get(
                "name",
                ""
            )

            if name.lower() == "eiin":

                selected_form = form

                break

        if selected_form:
            break

    if selected_form is None:

        raise RuntimeError(
            "EIIN form not found."
        )

    action = selected_form.get(
        "action",
        ""
    )

    method = selected_form.get(
        "method",
        "post"
    ).lower()

    action_url = urljoin(
        response.url,
        action
    )

    # --------------------------------------------------------
    # Build base form fields
    # --------------------------------------------------------

    base_fields = {}

    for inp in selected_form.find_all(
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
            "submit",
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

        base_fields[name] = inp.get(
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
        base_fields
    )

    return (
        response,
        selected_form,
        action_url,
        method,
        base_fields
    )


# ============================================================
# FIND EIIN FIELD
# ============================================================

def find_eiin_field(form):

    possible_names = [

        "eiin",
        "EIIN",
        "institute",
        "institute_eiin",
        "institute_eiin_no",
        "institute_no",
        "institute_id",

    ]

    input_names = {}

    for inp in form.find_all(
        "input"
    ):

        name = inp.get(
            "name"
        )

        if name:

            input_names[
                name
            ] = inp

    for name in possible_names:

        if name in input_names:

            return name

    for name, inp in input_names.items():

        placeholder = clean_text(
            inp.get(
                "placeholder",
                ""
            )
        ).lower()

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

            return name

    return None


# ============================================================
# PARSE INSTITUTION RESULT
# ============================================================

def parse_result(
    html,
    eiin,
    fallback_name
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

    result = {

        "eiin":
            str(eiin),

        "institution_name":
            fallback_name,

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
            gpa5,

        "year":
            YEAR,

        "board":
            BOARD,

    }

    # ========================================================
    # INSTITUTE NAME
    # ========================================================

    patterns = [

        r"INSTITUTE\s+NAME\s*:\s*(.+?)"
        r"\s*\(\s*"
        + re.escape(str(eiin))
        + r"\s*\)",

        r"INSTITUTE\s+NAME\s*:\s*(.+?)"
        r"\s+ZILLA\s*:",

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

            if name:

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
    # TOTAL GPA
    # ========================================================

    # Board institution result-এর GPA5-ই
    # এখানে total_gpa হিসেবে ব্যবহার করা হচ্ছে.

    result[
        "total_gpa"
    ] = result[
        "gpa5"
    ]

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
            appeared is not None
            and appeared > 0
            and passed is not None
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
# LOAD CHECKPOINT
# ============================================================

def load_checkpoint():

    if not OUTPUT_FILE.exists():

        return []

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            list
        ):

            return []

        return data

    except Exception:

        print(
            "WARNING: Could not read existing output."
        )

        return []


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    results
):

    # --------------------------------------------------------
    # Sort by EIIN
    # --------------------------------------------------------

    results = sorted(
        results,
        key=lambda x:
            int(x["eiin"])
    )

    temp_file = OUTPUT_FILE.with_suffix(
        ".tmp"
    )

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )

    temp_file.replace(
        OUTPUT_FILE
    )


# ============================================================
# SAVE FAILED
# ============================================================

def save_failed(
    failed
):

    failed = sorted(
        failed,
        key=lambda x:
            int(x["eiin"])
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


# ============================================================
# LOAD FAILED
# ============================================================

def load_failed():

    if not FAILED_FILE.exists():

        return []

    try:

        with open(
            FAILED_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            list
        ):

            return data

    except Exception:

        pass

    return []


# ============================================================
# COLLECT ONE INSTITUTION
# ============================================================

def collect_institution(
    eiin,
    institution_name,
    action_url,
    method,
    base_fields,
    eiin_field
):

    data = dict(
        base_fields
    )

    data[
        eiin_field
    ] = str(eiin)

    print()
    print(
        "-" * 70
    )

    print(
        f"EIIN: {eiin}"
    )

    print(
        f"Institution: {institution_name}"
    )

    print(
        "REQUEST START:",
        eiin
    )

    try:

        if method == "get":

            response = session.get(
                action_url,
                params=data,
                headers={
                    "Referer":
                        INDEX_URL
                },
                timeout=TIMEOUT
            )

        else:

            response = session.post(
                action_url,
                data=data,
                headers={

                    "Referer":
                        INDEX_URL,

                    "Origin":
                        "https://sresult.bise-ctg.gov.bd",

                },
                timeout=TIMEOUT
            )

    except Exception as error:

        print(
            "REQUEST ERROR:",
            eiin,
            "|",
            error
        )

        return None

    print(
        "REQUEST DONE:",
        eiin,
        "| HTTP",
        response.status_code
    )

    if response.status_code >= 400:

        print(
            "HTTP ERROR:",
            response.status_code
        )

        return None

    print(
        "PARSING RESULT..."
    )

    result = parse_result(
        response.text,
        eiin,
        institution_name
    )

    # --------------------------------------------------------
    # Validate result
    # --------------------------------------------------------

    if (
        not result["district"]
        and
        not result["thana"]
        and
        result["appeared"] is None
        and
        result["passed"] is None
        and
        result["gpa5"] is None
    ):

        print(
            "RESULT DATA NOT FOUND"
        )

        return None

    print(
        "FOUND:",
        result["institution_name"]
    )

    print(
        "District:",
        result["district"]
    )

    print(
        "Thana:",
        result["thana"]
    )

    print(
        "Appeared:",
        result["appeared"]
    )

    print(
        "Passed:",
        result["passed"]
    )

    print(
        "Passing Rate:",
        result["passing_rate"]
    )

    print(
        "GPA5:",
        result["gpa5"]
    )

    print(
        "Total GPA:",
        result["total_gpa"]
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    start = time.time()

    print()
    print("=" * 70)
    print("SSC 2026 INSTITUTION COLLECTION")
    print("=" * 70)

    print(
        "TEST MODE:",
        TEST_MODE
    )

    print(
        "TEST EIIN:",
        TEST_EIIN
    )

    print(
        "EXPECTED INSTITUTIONS:",
        EXPECTED_INSTITUTIONS
    )

    print(
        "MIN_DELAY:",
        MIN_DELAY
    )

    print(
        "MAX_DELAY:",
        MAX_DELAY
    )

    print("=" * 70)

    # ========================================================
    # STEP 1
    # ========================================================

    institutions = download_master_list()

    if not institutions:

        raise SystemExit(
            "No institutions found."
        )

    # ========================================================
    # TEST MODE
    # ========================================================

    if TEST_MODE:

        institutions = [

            item

            for item
            in institutions

            if item["eiin"]
            == str(TEST_EIIN)

        ]

        if not institutions:

            raise SystemExit(
                f"TEST EIIN {TEST_EIIN} "
                "not found."
            )

    # ========================================================
    # STEP 2
    # ========================================================

    (
        index_response,
        form,
        action_url,
        method,
        base_fields

    ) = open_result_form()

    eiin_field = find_eiin_field(
        form
    )

    if eiin_field is None:

        raise SystemExit(
            "EIIN input field not found."
        )

    print(
        "EIIN field detected:",
        eiin_field
    )

    # ========================================================
    # CHECKPOINT
    # ========================================================

    if TEST_MODE:

        results = []

        failed = []

    else:

        results = load_checkpoint()

        failed = load_failed()

    # --------------------------------------------------------
    # Existing EIIN set
    # --------------------------------------------------------

    collected_eiins = {

        str(item["eiin"])

        for item
        in results

    }

    failed_eiins = {

        str(item["eiin"])

        for item
        in failed

    }

    print()
    print(
        "=" * 70
    )

    print(
        "CHECKPOINT"
    )

    print(
        "Already collected:",
        len(collected_eiins)
    )

    print(
        "Previously failed:",
        len(failed_eiins)
    )

    print(
        "=" * 70
    )

    # ========================================================
    # COLLECTION
    # ========================================================

    total = len(
        institutions
    )

    processed = 0

    successful = 0

    failed_this_run = 0

    skipped = 0

    for index, institution in enumerate(
        institutions,
        start=1
    ):

        eiin = str(
            institution["eiin"]
        )

        name = institution[
            "institution_name"
        ]

        # ----------------------------------------------------
        # Skip already collected
        # ----------------------------------------------------

        if (
            not TEST_MODE
            and
            eiin in collected_eiins
        ):

            skipped += 1

            continue

        # ----------------------------------------------------
        # Skip previously failed
        #
        # Failed items are retried in this run only if
        # they are not already in results.
        # ----------------------------------------------------

        print()
        print(
            f"[{index}/{total}]"
        )

        result = collect_institution(

            eiin,

            name,

            action_url,

            method,

            base_fields,

            eiin_field

        )

        processed += 1

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if result is not None:

            results.append(
                result
            )

            collected_eiins.add(
                eiin
            )

            successful += 1

            # Remove from failed if
            # previously failed

            failed = [

                item

                for item
                in failed

                if str(
                    item["eiin"]
                ) != eiin

            ]

            failed_eiins.discard(
                eiin
            )

        # ----------------------------------------------------
        # FAILED
        # ----------------------------------------------------

        else:

            failed_this_run += 1

            if eiin not in failed_eiins:

                failed.append({

                    "eiin":
                        eiin,

                    "institution_name":
                        name,

                    "year":
                        YEAR,

                    "board":
                        BOARD,

                    "error":
                        "Result parsing/request failed"

                })

                failed_eiins.add(
                    eiin
                )

        # ----------------------------------------------------
        # CHECKPOINT SAVE
        # ----------------------------------------------------

        save_results(
            results
        )

        save_failed(
            failed
        )

        # ----------------------------------------------------
        # DELAY
        # ----------------------------------------------------

        if (
            index < total
            and not TEST_MODE
        ):

            delay = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            time.sleep(
                delay
            )

    # ========================================================
    # FINAL SAVE
    # ========================================================

    save_results(
        results
    )

    save_failed(
        failed
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    elapsed = round(
        time.time() - start,
        2
    )

    remaining = max(
        0,
        total - len(results)
    )

    print()
    print("=" * 70)
    print("SSC 2026 INSTITUTION COLLECTION COMPLETE")
    print("=" * 70)

    print(
        "Master institutions:",
        total
    )

    print(
        "Processed this run:",
        processed
    )

    print(
        "Successful this run:",
        successful
    )

    print(
        "Failed this run:",
        failed_this_run
    )

    print(
        "Skipped already collected:",
        skipped
    )

    print(
        "Total institutions saved:",
        len(results)
    )

    print(
        "Remaining:",
        remaining
    )

    print(
        "Failed file entries:",
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

    print("=" * 70)

    print(
        "DONE"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()