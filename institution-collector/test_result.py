import requests
from bs4 import BeautifulSoup


RESULT_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"

EIIN = "103086"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    )
}


def main():

    print("=" * 60)
    print("SSC 2026 INSTITUTION RESULT TEST")
    print("=" * 60)

    print()
    print("EIIN:", EIIN)

    print()
    print("URL:")
    print(RESULT_URL)

    try:

        response = requests.get(
            RESULT_URL,
            headers=HEADERS,
            timeout=30
        )

        print()
        print("HTTP Status:", response.status_code)

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
        print("REQUEST ERROR:")
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
    print("FORMS:")

    forms = soup.find_all("form")

    print(
        "Total forms:",
        len(forms)
    )


    for number, form in enumerate(
        forms,
        start=1
    ):

        print()
        print(
            "Form",
            number
        )

        print(
            "Action:",
            form.get("action")
        )

        print(
            "Method:",
            form.get("method")
        )


        inputs = form.find_all("input")


        for field in inputs:

            print(
                "INPUT:",
                "name=",
                field.get("name"),
                "| type=",
                field.get("type"),
                "| value=",
                field.get("value")
            )


    print()
    print("TABLES:")

    tables = soup.find_all("table")

    print(
        "Total tables:",
        len(tables)
    )


    for number, table in enumerate(
        tables,
        start=1
    ):

        rows = table.find_all("tr")

        print(
            "Table",
            number,
            "| rows:",
            len(rows)
        )


    print()
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    main()