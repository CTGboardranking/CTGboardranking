import requests
from bs4 import BeautifulSoup

BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"
INDIVIDUAL_URL = BASE_URL + "individual/"
RESULT_URL = BASE_URL + "result.php"

ROLL = "100001"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": INDIVIDUAL_URL
}

session = requests.Session()

print("Opening SSC Individual Result page...")

r = session.get(
    INDIVIDUAL_URL,
    headers=headers,
    timeout=30
)

print("GET Status:", r.status_code)

if r.status_code != 200:
    raise SystemExit("Could not open individual result page.")

print("Submitting Roll:", ROLL)

data = {
    "roll": ROLL,
    "button2": "Submit"
}

result = session.post(
    RESULT_URL,
    data=data,
    headers=headers,
    timeout=30,
    allow_redirects=True
)

print("POST Status:", result.status_code)
print("Final URL:", result.url)
print("Result Page Size:", len(result.content))

# Save returned HTML
with open(
    "scraper/result_page.html",
    "w",
    encoding="utf-8"
) as f:
    f.write(result.text)

print("\n===== RESULT PAGE TEXT =====\n")

soup = BeautifulSoup(result.text, "html.parser")

text = soup.get_text(
    "\n",
    strip=True
)

print(text[:5000])

print("\n===== TABLES =====")

tables = soup.find_all("table")

print("Tables found:", len(tables))

for i, table in enumerate(tables, 1):

    print(f"\n--- TABLE {i} ---")

    rows = table.find_all("tr")

    for row in rows:

        cells = row.find_all(
            ["th", "td"]
        )

        values = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in cells
        ]

        if values:
            print(values)

print("\n===== DONE =====")