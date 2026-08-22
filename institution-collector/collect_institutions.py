import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

SOURCE_URL = "https://esifssc.bise-ctg.gov.bd/esif_accounts.php"

OUTPUT_FILE = Path("institutions.json")

TIMEOUT = 30


# =========================================================
# HEADERS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    )
}


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\xa0", " ")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


# =========================================================
# NUMBER
# =========================================================

def to_number(value):

    value = clean_text(value)

    if not value:
        return 0

    value = value.replace(",", "")

    match = re.search(r"\d+", value)

    if not match:
        return 0

    return int(match.group())


# =========================================================
# DOWNLOAD PAGE
# =========================================================

def download_page():

    print()
    print("=" * 60)
    print("Downloading Institution Master List...")
    print("=" * 60)

    try:

        response = requests.get(
            SOURCE_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        print("HTTP Status:", response.status_code)

        response.raise_for_status()

        response.encoding = response.apparent_encoding

        return response.text

    except Exception as error:

        print()
        print("ERROR:", error)

        return None


# =========================================================
# FIND INSTITUTION TABLE
# =========================================================

def find_table(soup):

    tables = soup.find_all("table")

    print("Tables found:", len(tables))

    for table in tables:

        headers = []

        first_row = table.find("tr")

        if not first_row:
            continue

        for cell in first_row.find_all(
            ["th", "td"]
        ):

            headers.append(
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                ).lower()
            )

        header_text = " ".join(headers)

        if (
            "eiin" in header_text
            and "institute name" in header_text
        ):

            print("Institution table found.")

            return table

    return None


# =========================================================
# PARSE INSTITUTIONS
# =========================================================

def parse_institutions(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    table = find_table(soup)

    if table is None:

        raise RuntimeError(
            "Institution table could not be found."
        )


    rows = table.find_all("tr")

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


        # -------------------------------------------------
        # Expected columns
        #
        # 0 = SL
        # 1 = EIIN
        # 2 = INSTITUTE NAME
        # 3 = TOTAL STUDENTS
        # -------------------------------------------------

        if len(values) >= 4:

            eiin = values[1]

            institution_name = values[2]

            total_students = values[3]

        else:

            eiin = values[0]

            institution_name = values[1]

            total_students = values[2]


        # Skip header

        if (
            "eiin" in eiin.lower()
            or "institute" in institution_name.lower()
        ):

            continue


        # EIIN validation

        if not eiin.isdigit():

            continue


        eiin = int(eiin)


        # Institution name validation

        if not institution_name:

            continue


        total_students = to_number(
            total_students
        )


        institutions.append({

            "eiin": eiin,

            "institution_name":
                institution_name,

            "total_students":
                total_students,

            "year": 2026,

            "board":
                "Chattogram",

            "source":
                SOURCE_URL

        })


    return institutions


# =========================================================
# REMOVE DUPLICATES
# =========================================================

def remove_duplicates(institutions):

    unique = {}

    for item in institutions:

        eiin = item["eiin"]

        unique[eiin] = item


    return list(
        unique.values()
    )


# =========================================================
# SORT
# =========================================================

def sort_institutions(institutions):

    return sorted(
        institutions,
        key=lambda item:
            item["eiin"]
    )


# =========================================================
# SAVE JSON
# =========================================================

def save_json(institutions):

    data = {

        "metadata": {

            "title":
                "Chattogram Board Institution Master Data",

            "year":
                2026,

            "board":
                "Chattogram",

            "total_institutions":
                len(institutions),

            "source":
                SOURCE_URL

        },

        "institutions":
            institutions

    }


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# SHOW SAMPLE
# =========================================================

def show_sample(institutions):

    print()
    print("=" * 60)
    print("FIRST 10 INSTITUTIONS")
    print("=" * 60)

    for item in institutions[:10]:

        print(
            item["eiin"],
            "|",
            item["institution_name"],
            "| Students:",
            item["total_students"]
        )


# =========================================================
# MAIN
# =========================================================

def main():

    start_time = time.time()


    html = download_page()


    if not html:

        return


    try:

        institutions = parse_institutions(
            html
        )

    except Exception as error:

        print()
        print(
            "Parsing ERROR:",
            error
        )

        return


    print()
    print(
        "Institutions collected:",
        len(institutions)
    )


    institutions = remove_duplicates(
        institutions
    )


    institutions = sort_institutions(
        institutions
    )


    print(
        "Unique institutions:",
        len(institutions)
    )


    if not institutions:

        print()
        print(
            "No institution data found."
        )

        return


    save_json(
        institutions
    )


    show_sample(
        institutions
    )


    elapsed = round(
        time.time() - start_time,
        2
    )


    print()
    print("=" * 60)
    print("COLLECTION COMPLETED")
    print("=" * 60)

    print(
        "Total institutions:",
        len(institutions)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print(
        "Time:",
        elapsed,
        "seconds"
    )

    print("=" * 60)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()