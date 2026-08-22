import json
import os
import time
import requests
from bs4 import BeautifulSoup

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

        print("=" * 60, flush=True)
        print("RESUME MODE", flush=True)
        print(f"Previously collected: {len(results)}", flush=True)
        print("=" * 60, flush=True)

    except Exception as e:

        print("Could not load previous result file.", flush=True)
        print("Starting from beginning.", flush=True)
        print("Error:", e, flush=True)

# ============================================================
# EXISTING EIIN SET
# ============================================================

existing_eiins = set()

for item in results:

    eiin = str(item.get("eiin", "")).strip()

    if eiin:
        existing_eiins.add(eiin)

print(f"Existing EIIN records: {len(existing_eiins)}", flush=True)

# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
})

# ============================================================
# PARSE RESULT
# ============================================================

def parse_result(html, institution):

    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ", strip=True)

    institution_name = institution.get("institution_name", "")
    district = institution.get("district", "")
    thana = institution.get("thana", "")

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

            cells = row.find_all(["td", "th"])

            if len(cells) < 2:
                continue

            key = cells[0].get_text(" ", strip=True).upper()
            value = cells[1].get_text(" ", strip=True)

            if "APP" in key:
                try:
                    appeared = int(value)
                except:
                    pass

            elif "PASS" == key:
                try:
                    passed = int(value)
                except:
                    pass

            elif "PERCENT" in key:

                try:
                    passing_rate = float(
                        value.replace("%", "").strip()
                    )
                except:
                    pass

            elif "GPA5" in key or "GPA-5" in key:

                try:
                    gpa5 = int(value)
                except:
                    pass

    # --------------------------------------------------------
    # FALLBACK TEXT PARSING
    # --------------------------------------------------------

    import re

    if appeared is None:

        match = re.search(
            r"APP\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            appeared = int(match.group(1))

    if passed is None:

        match = re.search(
            r"PASS\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            passed = int(match.group(1))

    if passing_rate is None:

        match = re.search(
            r"PERCENT\s*:\s*([\d.]+)\s*%",
            text,
            re.IGNORECASE
        )

        if match:
            passing_rate = float(match.group(1))

    if gpa5 is None:

        match = re.search(
            r"GPA5\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            gpa5 = int(match.group(1))

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "eiin": str(institution.get("eiin", "")),
        "institution_name": institution_name,
        "district": district,
        "thana": thana,
        "appeared": appeared,
        "passed": passed,
        "passing_rate": passing_rate,
        "gpa5": gpa5
    }


# ============================================================
# COLLECTION
# ============================================================

limit = min(TEST_LIMIT, total)

print("=" * 60, flush=True)
print("STARTING COLLECTION", flush=True)
print(f"Target: {limit} institutions", flush=True)
print("=" * 60, flush=True)

for index in range(limit):

    institution = institutions[index]

    eiin = str(institution.get("eiin", "")).strip()

    name = institution.get(
        "institution_name",
        institution.get("name", "")
    )

    # --------------------------------------------------------
    # SKIP ALREADY COLLECTED
    # --------------------------------------------------------

    if eiin in existing_eiins:

        print(
            f"[{index + 1}/{limit}] SKIP - already collected: "
            f"{eiin}",
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
            data={"eiin": eiin},
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

            time.sleep(REQUEST_DELAY)

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
            f"PASSING RATE: {result['passing_rate']}%",
            flush=True
        )

        print(
            f"GPA-5: {result['gpa5']}",
            flush=True
        )

        # ----------------------------------------------------
        # SAVE IMMEDIATELY
        # ----------------------------------------------------

        results.append(result)

        existing_eiins.add(eiin)

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
            "ERROR: Request timeout - skipping institution",
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

    time.sleep(REQUEST_DELAY)


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