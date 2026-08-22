import json
import time
import re
import requests
from bs4 import BeautifulSoup


# =========================================================
# SETTINGS
# =========================================================

INPUT_FILE = "institution-collector/institutions.json"

OUTPUT_FILE = "institution-collector/institution_results.json"

BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"

RESULT_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/resultm.php"

TEST_LIMIT = 1286

REQUEST_DELAY = 0.3


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Referer": BASE_URL
}


# =========================================================
# NUMBER
# =========================================================

def to_number(value):

    if value is None:
        return 0

    value = str(value).strip()

    value = value.replace(",", "")

    value = value.replace("%", "")

    try:

        return float(value)

    except:

        return 0


# =========================================================
# EIIN
# =========================================================

def get_eiin(item):

    keys = [
        "eiin",
        "EIIN",
        "institute_code",
        "institution_code",
        "code"
    ]

    for key in keys:

        if key in item:

            value = str(
                item[key]
            ).strip()

            if value:

                return value

    return ""


# =========================================================
# INSTITUTION NAME
# =========================================================

def get_name(item):

    keys = [
        "institution",
        "institution_name",
        "institutionName",
        "institute",
        "institute_name",
        "college",
        "college_name",
        "name"
    ]

    for key in keys:

        if key in item:

            value = str(
                item[key]
            ).strip()

            if value:

                return value

    return ""


# =========================================================
# PARSE RESULT
# =========================================================

def parse_result(html, eiin):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    text = soup.get_text(
        " ",
        strip=True
    )


    result = {

        "eiin": eiin,

        "institution_name": "",

        "district": "",

        "thana": "",

        "appeared": 0,

        "passed": 0,

        "passing_rate": 0,

        "gpa5": 0

    }


    # -----------------------------------------------------
    # INSTITUTE NAME
    # -----------------------------------------------------

    match = re.search(
        r"INSTITUTE NAME\s*:\s*(.*?)\(\s*"
        + re.escape(eiin)
        + r"\s*\)",
        text,
        re.IGNORECASE
    )


    if match:

        result["institution_name"] = (
            match.group(1).strip()
        )


    # -----------------------------------------------------
    # DISTRICT
    # -----------------------------------------------------

    match = re.search(
        r"ZILLA\s*:\s*(.*?)\(\s*\d+\s*\)",
        text,
        re.IGNORECASE
    )


    if match:

        result["district"] = (
            match.group(1).strip()
        )


    # -----------------------------------------------------
    # THANA
    # -----------------------------------------------------

    match = re.search(
        r"THANA\s*:\s*(.*?)\(\s*\d+\s*\)",
        text,
        re.IGNORECASE
    )


    if match:

        result["thana"] = (
            match.group(1).strip()
        )


    # -----------------------------------------------------
    # APP
    # -----------------------------------------------------

    match = re.search(
        r"\bAPP\s*:\s*([0-9,]+)",
        text,
        re.IGNORECASE
    )


    if match:

        result["appeared"] = int(
            to_number(
                match.group(1)
            )
        )


    # -----------------------------------------------------
    # PASS
    # -----------------------------------------------------

    match = re.search(
        r"\bPASS\s*:\s*([0-9,]+)",
        text,
        re.IGNORECASE
    )


    if match:

        result["passed"] = int(
            to_number(
                match.group(1)
            )
        )


    # -----------------------------------------------------
    # PERCENT
    # -----------------------------------------------------

    match = re.search(
        r"\bPERCENT\s*:\s*([0-9.]+)\s*%",
        text,
        re.IGNORECASE
    )


    if match:

        result["passing_rate"] = round(
            to_number(
                match.group(1)
            ),
            2
        )


    # -----------------------------------------------------
    # GPA5
    # -----------------------------------------------------

    match = re.search(
        r"\bGPA5\s*:\s*([0-9,]+)",
        text,
        re.IGNORECASE
    )


    if match:

        result["gpa5"] = int(
            to_number(
                match.group(1)
            )
        )


    return result


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)

    print(
        "SSC 2026 INSTITUTION RESULT COLLECTOR"
    )

    print("=" * 60)


    # -----------------------------------------------------
    # LOAD INSTITUTIONS
    # -----------------------------------------------------

    print()

    print(
        "Loading:",
        INPUT_FILE
    )


    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    if isinstance(data, list):

        institutions = data

    elif isinstance(data, dict):

        if isinstance(
            data.get("institutions"),
            list
        ):

            institutions = (
                data["institutions"]
            )

        elif isinstance(
            data.get("data"),
            list
        ):

            institutions = (
                data["data"]
            )

        elif isinstance(
            data.get("results"),
            list
        ):

            institutions = (
                data["results"]
            )

        else:

            raise ValueError(
                "Unknown institutions.json format"
            )

    else:

        raise ValueError(
            "Invalid institutions.json"
        )


    print()

    print(
        "Total institutions:",
        len(institutions)
    )


    # -----------------------------------------------------
    # TEST LIMIT
    # -----------------------------------------------------

    test_institutions = (
        institutions[:TEST_LIMIT]
    )


    print()

    print(
        "TEST LIMIT:",
        TEST_LIMIT
    )


    # -----------------------------------------------------
    # SESSION
    # -----------------------------------------------------

    session = requests.Session()


    results = []


    # -----------------------------------------------------
    # COLLECT
    # -----------------------------------------------------

    for index, institution in enumerate(
        test_institutions,
        start=1
    ):

        eiin = get_eiin(
            institution
        )


        name = get_name(
            institution
        )


        print()

        print("-" * 60)

        print(
            f"[{index}/{len(test_institutions)}]"
        )

        print(
            "EIIN:",
            eiin
        )

        print(
            "Institution:",
            name
        )


        if not eiin:

            print(
                "SKIPPED: EIIN not found"
            )

            continue


        try:

            # -------------------------------------------------
            # INITIAL REQUEST
            # -------------------------------------------------

            session.get(
                BASE_URL,
                headers=HEADERS,
                timeout=30
            )


            # -------------------------------------------------
            # RESULT REQUEST
            # -------------------------------------------------

            response = session.post(

                RESULT_URL,

                data={
                    "eiin": eiin
                },

                headers=HEADERS,

                timeout=30
            )


            print(
                "HTTP:",
                response.status_code
            )


            if response.status_code != 200:

                print(
                    "FAILED HTTP STATUS"
                )

                continue


            result = parse_result(
                response.text,
                eiin
            )


            # -------------------------------------------------
            # FALLBACK NAME
            # -------------------------------------------------

            if not result[
                "institution_name"
            ]:

                result[
                    "institution_name"
                ] = name


            results.append(
                result
            )


            print(
                "APP:",
                result["appeared"]
            )


            print(
                "PASS:",
                result["passed"]
            )


            print(
                "PASSING RATE:",
                str(
                    result["passing_rate"]
                ) + "%"
            )


            print(
                "GPA-5:",
                result["gpa5"]
            )


        except Exception as error:

            print(
                "ERROR:",
                error
            )


        # -----------------------------------------------------
        # DELAY
        # -----------------------------------------------------

        time.sleep(
            REQUEST_DELAY
        )


    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    print()

    print("=" * 60)

    print(
        "SAVING RESULT DATA"
    )

    print("=" * 60)


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


    print()

    print(
        "Results collected:",
        len(results)
    )


    print(
        "Output:",
        OUTPUT_FILE
    )


    print()

    print("=" * 60)

    print(
        "COLLECTION TEST COMPLETED"
    )

    print("=" * 60)


if __name__ == "__main__":

    main()