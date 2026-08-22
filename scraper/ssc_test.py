import requests

URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/individual/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://sresult.bise-ctg.gov.bd/"
}

print("Connecting to Chattogram Board...")
print("URL:", URL)

try:
    session = requests.Session()

    response = session.get(
        URL,
        headers=headers,
        timeout=30
    )

    print("HTTP Status:", response.status_code)
    print("Page Size:", len(response.content))
    print("Final URL:", response.url)

    print("\nFirst 500 characters:\n")
    print(response.text[:500])

    if response.status_code != 200:
        raise SystemExit(
            f"Board server returned HTTP {response.status_code}"
        )

except requests.RequestException as e:
    print("Request Error:", e)
    raise SystemExit(1)
