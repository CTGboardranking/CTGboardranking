import requests
from bs4 import BeautifulSoup


BASE_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"

RESULT_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/resultm.php"

EIIN = "103086"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Referer": BASE_URL
}


def main():

    print("=" * 60)
    print("SSC 2026 INSTITUTION RESULT POST TEST")
    print("=" * 60)

    print()
    print("EIIN:", EIIN)

    print()
    print("POST URL:")

    print(RESULT_URL)


    session = requests.Session()


    try:

        first_response = session.get(
            BASE_URL,
            headers=HEADERS,
            timeout=30
        )


        print()
        print(
            "Initial HTTP Status:",
            first_response.status_code
        )


        first_response.raise_for_status()


    except Exception as error:

        print()
        print("INITIAL REQUEST ERROR:")

        print(error)

        return


    try:

        response = session.post(
            RESULT_URL,
            data={
                "eiin": EIIN
            },
            headers=HEADERS,
            timeout=30
        )


        print()
        print(
            "POST HTTP Status:",
            response.status_code
        )


        print(
            "Content-Type:",
            response.headers.get(
                "content-type",
                ""
            )
        )


        print(
            "Response Length:",
            len(response.text)
        )


        response.raise_for_status()


    except Exception as error:

        print()
        print("POST REQUEST ERROR:")

        print(error)

        return


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    title = soup.find("title")


    print()
    print("PAGE TITLE:")


    if title:

        print(
            title.get_text(
                " ",
                strip=True
            )
        )

    else:

        print("Not found")


    print()
    print("TABLES:")


    tables = soup.find_all("table")


    print(
        "Total tables:",
        len(tables)
    )


    for table_number, table in enumerate(
        tables,
        start=1
    ):

        rows = table.find_all("tr")


        print()
        print(
            "TABLE",
            table_number,
            "| Rows:",
            len(rows)
        )


        for row in rows[:10]:

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

                print(
                    " | ".join(values)
                )


    print()
    print("IMPORTANT TEXT:")


    text = soup.get_text(
        " ",
        strip=True
    )


    print(
        text[:3000]
    )


    print()
    print("=" * 60)
    print("POST TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    main()