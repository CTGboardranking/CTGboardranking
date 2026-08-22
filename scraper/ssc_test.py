import requests
from bs4 import BeautifulSoup

URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/individual/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session()

print("Connecting to Chattogram Board...")

response = session.get(
    URL,
    headers=headers,
    timeout=30
)

print("HTTP Status:", response.status_code)
print("Page Size:", len(response.content))

if response.status_code != 200:
    raise SystemExit(1)

soup = BeautifulSoup(response.text, "html.parser")

print("\n===== FORMS =====")

for i, form in enumerate(soup.find_all("form"), 1):

    print(f"\nFORM {i}")
    print("Action:", form.get("action"))
    print("Method:", form.get("method"))

    for inp in form.find_all(["input", "select", "button"]):

        print(
            " ",
            inp.name,
            "name=",
            inp.get("name"),
            "type=",
            inp.get("type"),
            "value=",
            inp.get("value")
        )

print("\n===== PAGE TEXT =====")
print(soup.get_text(" ", strip=True)[:1500])
