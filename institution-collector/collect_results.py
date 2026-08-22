import json
import os
import time
import requests
from bs4 import BeautifulSoup
import re

# ============================================================
# SETTINGS
# ============================================================

INPUT_FILE = "institution-collector/institutions.json"
OUTPUT_FILE = "institution-collector/institution_results.json"

REQUEST_DELAY = 0.3
TEST_LIMIT = 1286

BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/resultm.php"

TIMEOUT = 30

# ============================================================
# LOAD INSTITUTIONS
# ============================================================

print("=" * 60, flush=True)
print("SSC 2026 INSTITUTION RESULT COLLECTOR", flush=True)
print("=" * 60, flush=True)

print(f"Loading: {INPUT_FILE}", flush=True)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    institutions = json.load(f)

# ------------------------------------------------------------
# NORMALIZE INSTITUTION DATA
# ------------------------------------------------------------

if isinstance(institutions, dict):

    normalized = []

    for key, value in institutions.items():

        if isinstance(value, dict):

            item = value.copy()

            # If EIIN is missing, use dictionary key as EIIN
            if not item.get("eiin"):
                item["eiin"] = str(key)

            normalized.append(item)

    institutions = normalized

elif isinstance(institutions, list):

    # Already correct format
    institutions = institutions

else:

    raise ValueError(
        "institutions.json must contain a JSON list or dictionary"
    )

total = len(institutions)

print(f"Total institutions: {total}", flush=True)
print(f"TEST LIMIT: {TEST_LIMIT}", flush=True)

# ============================================================
# LOAD PREVIOUS RESULTS
# ============================================================

results = []

if os.path.exists(OUTPUT_FILE):

    try:

        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            old_results = json.load(f)

        if isinstance(old_results, list):

            results = old_results

        else:

            print(
                "WARNING: Previous result file is not a list.",
                flush=True
            )

        print("=" * 60, flush=True)
        print("RESUME MODE", flush=True)
        print(
            f"Previously collected: {len(results)}",
            flush=True
        )
        print("=" * 60, flush=True)

    except Exception as e:

        print(
            "Could not load previous result file.",
            flush=True
        )

        print(
            "Starting from beginning.",
            flush=True
        )

        print(
            "Error:",
            e,
            flush=True
        )

# ============================================================
# EXISTING EIIN SET
# ============================================================

existing_eiins = set()

for item in results:

    if not isinstance(item, dict):
        continue

    eiin = str(
        item.get("eiin", "")
    ).strip()

    if eiin:
        existing_eiins.add(eiin)

print(
    f"Existing EIIN records: {len(existing_eiins)}",
    flush=True
)

# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update({

    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "*/*;q=0.8"
    ),

    "Referer": BASE_URL

})

# ============================================================
# PARSE RESULT
# ============================================================

def parse_result(html, institution):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    institution_name = institution.get(
        "institution_name",
        institution.get("name", "")
    )

    district = institution.get(
        "district",
        ""
    )

    thana = institution.get(
        "thana",
        ""
    )

    appeared = None
    passed = None
    passing_rate = None
    gpa5 = None

    # --------------------------------------------------------
    # TABLE PARSING
    # --------------------------------------------------------

    tables = soup.find_all("table")

    for table in tables:

        rows = table.find_all("tr")

        for row in rows:

            cells = row.find_all(
                ["td", "th"]
            )

            if len(cells) < 2:
                continue

            key = cells[0].get_text(
                " ",
                strip=True
            ).upper()

            value = cells[1].get_text(
                " ",
                strip=True
            )

            # APP / APPEARED
            if (
                "APP" in key
                or "APPEARED" in key
            ):

                match = re.search(
                    r"\d+",
                    value
                )

                if match:
                    appeared = int(
                        match.group()
                    )

            # PASS
            elif "PASS" in key:

                match = re.search(
                    r"\d+",
                    value
                )

                if match:
                    passed = int(
                        match.group()
                    )

            # PERCENT / PASSING RATE
            elif (
                "PERCENT" in key
                or "RATE" in key
            ):

                match = re.search(
                    r"[\d.]+",
                    value
                )

                if match:
                    passing_rate = float(
                        match.group()
                    )

            # GPA-5
            elif (
                "GPA5" in key
                or "GPA-5" in key
                or "GPA 5" in key
            ):

                match = re.search(
                    r"\d+",
                    value
                )

                if match:
                    gpa5 = int(
                        match.group()
                    )

    # --------------------------------------------------------
    # FALLBACK TEXT PARSING
    # --------------------------------------------------------

    if appeared is None:

        match = re.search(
            r"APP(?:EARED)?\s*[:\-]?\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            appeared = int(
                match.group(1)
            )

    if passed is None:

        match = re.search(
            r"PASS(?:ED)?\s*[:\-]?\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            passed = int(
                match.group(1)
            )

    if passing_rate is None:

        match = re.search(
            r"(?:PERCENT|PASSING\s*RATE)"
            r"\s*[:\-]?\s*([\d.]+)\s*%?",
            text,
            re.IGNORECASE
        )

        if match:
            passing_rate = float(
                match.group(1)
            )

    if gpa5 is None:

        match = re.search(
            r"GPA[\s\-]*5\s*[:\-]?\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            gpa5 = int(
                match.group(1)
            )

    # --------------------------------------------------------
    # CALCULATE PASSING RATE IF NOT FOUND
    # --------------------------------------------------------

    if (
        passing_rate is None
        and appeared is not None
        and passed is not None
        and appeared > 0
    ):

        passing_rate = round(
            (passed / appeared) * 100,
            2
        )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {

        "eiin": str(
            institution.get(
                "eiin",
                ""
            )
        ).strip(),

        "institution_name":
            institution_name,

        "district":
            district,

        "thana":
            thana,

        "appeared":
            appeared,

        "passed":
            passed,

        "passing_rate":
            passing_rate,

        "gpa5":
            gpa5
    }


# ============================================================
# COLLECTION
# ============================================================

limit = min(
    TEST_LIMIT,
    total
)

print("=" * 60, flush=True)
print("STARTING COLLECTION", flush=True)
print(
    f"Target: {limit} institutions",
    flush=True
)
print("=" * 60, flush=True)

for index in range(limit):

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if index >= len(institutions):
        break

    institution = institutions[index]

    if not isinstance(institution, dict):

        print(
            f"[{index + 1}/{limit}] "
            f"SKIP - invalid institution data",
            flush=True
        )

        continue

    eiin = str(
        institution.get(
            "eiin",
            ""
        )
    ).strip()

    name = institution.get(
        "institution_name",
        institution.get(
            "name",
            ""
        )
    )

    # --------------------------------------------------------
    # SKIP INVALID EIIN
    # --------------------------------------------------------

    if not eiin:

        print(
            f"[{index + 1}/{limit}] "
            f"SKIP - EIIN missing",
            flush=True
        )

        continue

    # --------------------------------------------------------
    # SKIP ALREADY COLLECTED
    # --------------------------------------------------------

    if eiin in existing_eiins:

        print(
            f"[{index + 1}/{limit}] "
            f"SKIP - already collected: {eiin}",
            flush=True
        )

        continue

    print("-" * 60, flush=True)

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

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

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

            time.sleep(
                REQUEST_DELAY
            )

            continue

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        result = parse_result(
            response.text,
            institution
        )

        print(
            f"APP: {result['appeared']}",
            flush=True
        )

        print(
            f"PASS: {result['passed']}",
            flush=True
        )

        print(
            f"PASSING RATE: "
            f"{result['passing_rate']}%",
            flush=True
        )

        print(
            f"GPA-5: {result['gpa5']}",
            flush=True
        )

        # ----------------------------------------------------
        # SAVE IMMEDIATELY
        # ----------------------------------------------------

        results.append(
            result
        )

        existing_eiins.add(
            eiin
        )

        # Make sure output directory exists
        output_dir = os.path.dirname(
            OUTPUT_FILE
        )

        if output_dir:
            os.makedirs(
                output_dir,
                exist_ok=True
            )

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

        print(
            f"SAVED: {len(results)} results",
            flush=True
        )

    except requests.exceptions.Timeout:

        print(
            "ERROR: Request timeout - "
            "skipping institution",
            flush=True
        )

    except requests.exceptions.RequestException as e:

        print(
            f"ERROR: Request failed - {e}",
            flush=True
        )

    except Exception as e:

        print(
            f"ERROR: {e}",
            flush=True
        )

    # --------------------------------------------------------
    # DELAY
    # --------------------------------------------------------

    time.sleep(
        REQUEST_DELAY
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("=" * 60, flush=True)
print("COLLECTION COMPLETED", flush=True)
print("=" * 60, flush=True)

print(
    f"Results collected: {len(results)}",
    flush=True
)

print(
    f"Output: {OUTPUT_FILE}",
    flush=True
)

print("=" * 60, flush=True)