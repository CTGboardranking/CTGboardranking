import json
import os
import time
import re
import requests
from bs4 import BeautifulSoup

# ============================================================
# SETTINGS
# ============================================================

INPUT_FILE = "institution-collector/institutions.json"
OUTPUT_FILE = "institution-collector/student_results.json"

REQUEST_DELAY = 0.3

# প্রথমে 1 দিয়ে TEST করো
TEST_LIMIT = 1

BASE_URL = (
    "https://sresult.bise-ctg.gov.bd/"
    "to_ssc_26_ctg/resultm.php"
)

TIMEOUT = 30


# ============================================================
# START
# ============================================================

print("=" * 70, flush=True)
print("SSC 2026 STUDENT RESULT COLLECTOR", flush=True)
print("=" * 70, flush=True)


# ============================================================
# LOAD INSTITUTIONS
# ============================================================

print(
    f"Loading: {INPUT_FILE}",
    flush=True
)

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    raw_data = json.load(f)


# ============================================================
# SUPPORT YOUR institutions.json FORMAT
# ============================================================

if isinstance(raw_data, dict):

    if isinstance(
        raw_data.get("institutions"),
        list
    ):

        institutions = raw_data["institutions"]

    else:

        raise ValueError(
            "institutions.json does not contain "
            "'institutions' array"
        )

elif isinstance(raw_data, list):

    institutions = raw_data

else:

    raise ValueError(
        "Invalid institutions.json format"
    )


print(
    f"Raw institutions: {len(institutions)}",
    flush=True
)


# ============================================================
# VALID INSTITUTIONS
# ============================================================

valid_institutions = []

for item in institutions:

    if not isinstance(item, dict):
        continue

    eiin = str(
        item.get(
            "eiin",
            ""
        )
    ).strip()

    if not eiin:
        continue

    if not eiin.isdigit():
        continue

    valid_institutions.append(
        item
    )


institutions = valid_institutions

total = len(institutions)


print(
    f"Valid institutions: {total}",
    flush=True
)

print(
    f"TEST LIMIT: {TEST_LIMIT}",
    flush=True
)


# ============================================================
# LOAD PREVIOUS RESULTS
# ============================================================

results = []

if os.path.exists(
    OUTPUT_FILE
):

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            old_results = json.load(f)


        if isinstance(
            old_results,
            list
        ):

            results = old_results


        print(
            "=" * 70,
            flush=True
        )

        print(
            "RESUME MODE",
            flush=True
        )

        print(
            f"Previously collected: {len(results)}",
            flush=True
        )

        print(
            "=" * 70,
            flush=True
        )


    except Exception as e:

        print(
            "Could not load previous result file.",
            flush=True
        )

        print(
            f"Error: {e}",
            flush=True
        )


# ============================================================
# EXISTING KEYS
# ============================================================

existing_keys = set()

for item in results:

    if not isinstance(
        item,
        dict
    ):

        continue

    eiin = str(
        item.get(
            "eiin",
            ""
        )
    ).strip()

    roll = str(
        item.get(
            "roll",
            ""
        )
    ).strip()

    if eiin and roll:

        existing_keys.add(
            f"{eiin}:{roll}"
        )


print(
    f"Existing EIIN+Roll records: "
    f"{len(existing_keys)}",
    flush=True
)


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update({

    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36",

    "Accept":
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8",

    "Accept-Language":
        "en-US,en;q=0.9",

    "Connection":
        "keep-alive"

})


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def number(value):

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

    n = float(
        match.group(0)
    )

    if n.is_integer():

        return int(n)

    return n


def institution_name(item):

    return clean_text(
        item.get(
            "institution_name",
            ""
        )
    )


def district_name(item):

    return clean_text(
        item.get(
            "district",
            "Chattogram"
        )
    )


# ============================================================
# FIND ROLL
# ============================================================

def find_rolls(soup):

    rolls = set()

    # --------------------------------------------------------
    # Search table rows
    # --------------------------------------------------------

    for row in soup.find_all("tr"):

        cells = row.find_all(
            ["td", "th"]
        )

        if not cells:
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

        for value in values:

            matches = re.findall(
                r"\b\d{6,8}\b",
                value
            )

            for roll in matches:

                rolls.add(
                    roll
                )


    # --------------------------------------------------------
    # Search complete text
    # --------------------------------------------------------

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    matches = re.findall(
        r"\b\d{6,8}\b",
        text
    )

    for roll in matches:

        rolls.add(
            roll
        )


    return sorted(
        rolls
    )


# ============================================================
# FIND STUDENT TABLE
# ============================================================

def inspect_tables(soup):

    tables = soup.find_all(
        "table"
    )

    print(
        f"TABLES FOUND: {len(tables)}",
        flush=True
    )

    for index, table in enumerate(
        tables,
        start=1
    ):

        rows = table.find_all(
            "tr"
        )

        print(
            f"  Table {index}: "
            f"{len(rows)} rows",
            flush=True
        )

        if rows:

            first_row = rows[0]

            values = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )
                for cell in first_row.find_all(
                    ["td", "th"]
                )
            ]

            if values:

                print(
                    "    Columns:",
                    " | ".join(values[:15]),
                    flush=True
                )


# ============================================================
# PARSE STUDENT ROWS
# ============================================================

def parse_student_rows(
    soup,
    institution
):

    students = []

    tables = soup.find_all(
        "table"
    )

    for table in tables:

        rows = table.find_all(
            "tr"
        )

        for row in rows:

            cells = row.find_all(
                ["td", "th"]
            )

            if len(cells) < 2:
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

            joined = " ".join(
                values
            )

            # ------------------------------------------------
            # Find roll in row
            # ------------------------------------------------

            roll_match = re.search(
                r"\b\d{6,8}\b",
                joined
            )

            if not roll_match:
                continue

            roll = roll_match.group(
                0
            )

            # ------------------------------------------------
            # Try GPA
            # ------------------------------------------------

            gpa = None

            for value in values:

                match = re.search(
                    r"\b([0-5]\.\d{1,2})\b",
                    value
                )

                if match:

                    gpa = float(
                        match.group(1)
                    )

                    break

            # ------------------------------------------------
            # Save raw row
            # ------------------------------------------------

            students.append({

                "eiin":
                    str(
                        institution.get(
                            "eiin",
                            ""
                        )
                    ),

                "institution_name":
                    institution_name(
                        institution
                    ),

                "district":
                    district_name(
                        institution
                    ),

                "roll":
                    roll,

                "gpa":
                    gpa,

                "raw_row":
                    values

            })

    return students


# ============================================================
# SAVE
# ============================================================

def save_results():

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# COLLECTION
# ============================================================

limit = min(
    TEST_LIMIT,
    total
)


print("=" * 70, flush=True)

print(
    "STARTING STUDENT COLLECTION",
    flush=True
)

print(
    f"Target institutions: {limit}",
    flush=True
)

print("=" * 70, flush=True)


for index in range(limit):

    institution = institutions[index]

    eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()

    name = institution_name(
        institution
    )

    print(
        "-" * 70,
        flush=True
    )

    print(
        f"[{index + 1}/{limit}]",
        flush=True
    )

    print(
        f"EIIN: {eiin}",
        flush=True
    )

    print(
        f"Institution: {name}",
        flush=True
    )


    # ========================================================
    # REQUEST
    # ========================================================

    try:

        response = session.post(

            BASE_URL,

            data={
                "eiin": eiin
            },

            timeout=TIMEOUT

        )


        print(
            f"HTTP: {response.status_code}",
            flush=True
        )


        if response.status_code != 200:

            print(
                "ERROR: HTTP status is not 200",
                flush=True
            )

            continue


        # ====================================================
        # PARSE HTML
        # ====================================================

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # ====================================================
        # DEBUG TABLE STRUCTURE
        # ====================================================

        inspect_tables(
            soup
        )


        # ====================================================
        # FIND ROLLS
        # ====================================================

        rolls = find_rolls(
            soup
        )


        print(
            f"ROLLS DETECTED: {len(rolls)}",
            flush=True
        )


        if rolls:

            print(
                "Detected rolls:",
                ", ".join(
                    rolls[:20]
                ),
                flush=True
            )


        # ====================================================
        # PARSE STUDENT ROWS
        # ====================================================

        students = parse_student_rows(
            soup,
            institution
        )


        # ====================================================
        # IF NO STUDENTS
        # ====================================================

        if not students:

            print(
                "",
                flush=True
            )

            print(
                "NO STUDENT ROW FOUND",
                flush=True
            )

            print(
                "The current result page appears "
                "to be institution summary data.",
                flush=True
            )

            print(
                "Student-level endpoint/parameter "
                "needs to be identified.",
                flush=True
            )

            time.sleep(
                REQUEST_DELAY
            )

            continue


        # ====================================================
        # SAVE STUDENTS
        # ====================================================

        new_count = 0


        for student in students:

            roll = str(
                student.get(
                    "roll",
                    ""
                )
            ).strip()


            key = (
                f"{eiin}:{roll}"
            )


            if key in existing_keys:

                continue


            results.append(
                student
            )


            existing_keys.add(
                key
            )


            new_count += 1


        save_results()


        print(
            f"NEW STUDENTS SAVED: {new_count}",
            flush=True
        )


        print(
            f"TOTAL STUDENT RECORDS: "
            f"{len(results)}",
            flush=True
        )


    except requests.exceptions.Timeout:

        print(
            "ERROR: Request timeout",
            flush=True
        )


    except requests.exceptions.RequestException as e:

        print(
            f"ERROR: Request failed: {e}",
            flush=True
        )


    except Exception as e:

        print(
            f"ERROR: {e}",
            flush=True
        )


    time.sleep(
        REQUEST_DELAY
    )


# ============================================================
# FINAL
# ============================================================

print("=" * 70, flush=True)

print(
    "STUDENT COLLECTION COMPLETED",
    flush=True
)

print("=" * 70, flush=True)

print(
    f"Student records: {len(results)}",
    flush=True
)

print(
    f"Output: {OUTPUT_FILE}",
    flush=True
)

print("=" * 70, flush=True)