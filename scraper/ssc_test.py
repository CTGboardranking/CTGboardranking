import requests
from bs4 import BeautifulSoup
import json
import sys
import time


# ==========================================
# CONFIG
# ==========================================

BASE_URL = "https://sresult.bise-ctg.gov.bd/"


# ==========================================
# TEST ROLL
# ==========================================

ROLL = sys.argv[1] if len(sys.argv) > 1 else "100001"


# ==========================================
# SESSION
# ==========================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/130.0 Mobile Safari/537.36"
    )
})


# ==========================================
# REQUEST
# ==========================================

print("Connecting to Chattogram Board...")

try:

    response = session.get(
        BASE_URL,
        timeout=30
    )

    print("HTTP Status:", response.status_code)

    print("Page size:", len(response.text))

except Exception as e:

    print("Connection error:")
    print(e)

    sys.exit(1)


# ==========================================
# BASIC CHECK
# ==========================================

if response.status_code != 200:

    print("Website did not return HTTP 200.")

    sys.exit(1)


print()
print("Connection successful.")
print("Testing result page structure...")


# ==========================================
# PARSE HTML
# ==========================================

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


title = soup.title.text.strip() if soup.title else ""

print("Page title:", title)


# ==========================================
# FIND FORMS
# ==========================================

forms = soup.find_all("form")

print("Forms found:", len(forms))


for i, form in enumerate(forms, start=1):

    print()
    print("FORM", i)

    print(
        "Action:",
        form.get("action")
    )

    print(
        "Method:",
        form.get("method")
    )

    inputs = form.find_all(
        ["input", "select"]
    )

    for element in inputs:

        print(
            element.name,
            element.get("name"),
            element.get("id"),
            element.get("value")
        )


# ==========================================
# SAVE RESPONSE FOR INSPECTION
# ==========================================

with open(
    "scraper/result_page.html",
    "w",
    encoding="utf-8"
) as f:

    f.write(response.text)


print()
print(
    "Saved page as scraper/result_page.html"
)

print()
print("TEST COMPLETED.")