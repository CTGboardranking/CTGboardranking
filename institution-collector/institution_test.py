import json
import re
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIG
# ============================================================

EIIN_TO_TEST = "103086"

ESIF_URL = (
    "https://esifssc.bise-ctg.gov.bd/"
    "esif_accounts.php"
)

SSC_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/individual/"
)

TIMEOUT = 30


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
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
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# CLEAN
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\xa0", " ")

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# FIND INSTITUTION FROM ESIF
# ============================================================

def find_institution(eiin):

    print()
    print("=" * 70)
    print("STEP 1: SEARCHING INSTITUTION")
    print("=" * 70)

    print("EIIN:", eiin)
    print("URL:", ESIF_URL)

    try:

        response = requests.get(
            ESIF_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        print(
            "HTTP Status:",
            response.status_code
        )

        response.raise_for_status()

    except Exception as error:

        print(
            "ERROR:",
            error
        )

        return None


    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    for table in soup.find_all("table"):

        for row in table.find_all("tr"):

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

            if not values:
                continue


            if eiin not in values:
                continue


            print()
            print("✓ INSTITUTION FOUND")
            print("-" * 70)

            for index, value in enumerate(values):

                print(
                    f"[{index}] {value}"
                )


            # Expected:
            #
            # 0 = SL
            # 1 = EIIN
            # 2 = Institution Name
            # 3 = Total Students
            #

            result = {

                "eiin":
                    eiin,

                "institution_name":
                    values[2]
                    if len(values) > 2
                    else "",

                "total_students":
                    values[3]
                    if len(values) > 3
                    else "",

            }


            print()
            print(
                "Parsed institution:"
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2
                )
            )

            return result


    print()
    print(
        "✗ Institution not found."
    )

    return None


# ============================================================
# INSPECT SSC FORM
# ============================================================

def inspect_ssc_form():

    print()
    print("=" * 70)
    print("STEP 2: INSPECTING SSC RESULT FORM")
    print("=" * 70)

    print("URL:", SSC_URL)


    session = requests.Session()

    session.headers.update(
        HEADERS
    )


    try:

        response = session.get(
            SSC_URL,
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

    except Exception as error:

        print(
            "ERROR:",
            error
        )

        return


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    forms = soup.find_all("form")

    print(
        "Forms found:",
        len(forms)
    )


    if not forms:

        print(
            "✗ No form found."
        )

        return


    for form_number, form in enumerate(
        forms,
        start=1
    ):

        print()
        print(
            "-" * 70
        )

        print(
            f"FORM #{form_number}"
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
                "GET"
            )
        )


        print()
        print(
            "INPUT FIELDS:"
        )


        for inp in form.find_all(
            "input"
        ):

            print(
                json.dumps(
                    {
                        "name":
                            inp.get(
                                "name"
                            ),

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
                            ),

                    },
                    ensure_ascii=False
                )
            )


        print()
        print(
            "SELECT FIELDS:"
        )


        for select in form.find_all(
            "select"
        ):

            print(
                "SELECT:",
                select.get(
                    "name"
                )
            )


            for option in select.find_all(
                "option"
            ):

                print(
                    "   ",
                    "value=",
                    option.get(
                        "value",
                        ""
                    ),
                    "| text=",
                    clean_text(
                        option.get_text()
                    )
                )


# ============================================================
# PAGE TEXT SAMPLE
# ============================================================

def show_page_text():

    print()
    print("=" * 70)
    print("STEP 3: SSC PAGE TEXT SAMPLE")
    print("=" * 70)


    try:

        response = requests.get(
            SSC_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

    except Exception as error:

        print(
            "ERROR:",
            error
        )

        return


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )


    print()
    print(
        text[:5000]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SSC 2026 INSTITUTION TEST")
    print("=" * 70)

    print(
        "Testing EIIN:",
        EIIN_TO_TEST
    )


    institution = find_institution(
        EIIN_TO_TEST
    )


    if institution:

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
                institution,
                ensure_ascii=False,
                indent=2
            )
        )


    inspect_ssc_form()

    show_page_text()


    print()
    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()