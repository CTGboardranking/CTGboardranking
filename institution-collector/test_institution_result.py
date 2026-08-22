import requests
from bs4 import BeautifulSoup


RESULT_URL = "https://sresult.bise-ctg.gov.bd/to_ssc_26_ctg/"

TEST_EIIN = "YOUR_EIIN_HERE"


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
    print("INSTITUTION RESULT TEST")
    print("=" * 60)

    print()
    print("Result URL:")
    print(RESULT_URL)

    print()
    print("Test EIIN:")
    print(TEST_EIIN)

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


    print()
    print("Page title:")

    title = soup.find("title")

    if title:

        print(
            title.get_text(
                " ",
                strip=True
            )
        )

    else:

        print("No title found.")


    print()
    print("Forms found:")

    forms = soup.find_all("form")

    print(len(forms))


    for index, form in enumerate(
        forms,
        start=1
    ):

        print()
        print(
            "FORM",
            index
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


        for input_tag in inputs:

            print(
                "Input:",
                input_tag.get("name"),
                "| type:",
                input_tag.get("type"),
                "| value:",
                input_tag.get("value")
            )


    print()
    print("Tables found:")

    tables = soup.find_all("table")

    print(len(tables))


    print()
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    main()