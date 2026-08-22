/* =========================================================
   CTGBoardRanking — Main Script
========================================================= */


/* =========================================================
   DARK MODE
========================================================= */

const themeBtn = document.getElementById("themeBtn");

const savedTheme = localStorage.getItem("ctg-theme");

if (savedTheme === "dark") {
    document.body.classList.add("dark");
}

if (themeBtn) {

    themeBtn.addEventListener("click", () => {

        document.body.classList.toggle("dark");

        const dark =
            document.body.classList.contains("dark");

        localStorage.setItem(
            "ctg-theme",
            dark ? "dark" : "light"
        );

    });

}


/* =========================================================
   JSON PATH
========================================================= */

const DATA_PATH = "scraper/";


/* =========================================================
   LOAD JSON
========================================================= */

async function loadJSON(file) {

    try {

        const response = await fetch(
            DATA_PATH + file + "?v=" + Date.now()
        );

        if (!response.ok) {
            throw new Error(
                `${file}: HTTP ${response.status}`
            );
        }

        return await response.json();

    } catch (error) {

        console.warn(
            "Could not load:",
            file,
            error
        );

        return null;
    }
}


/* =========================================================
   NUMBER FORMAT
========================================================= */

function formatNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
        return value;
    }

    return number.toLocaleString("en-US");
}


/* =========================================================
   SAFE TEXT
========================================================= */

function safeText(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    return String(value);
}


/* =========================================================
   STUDENT RANKING
========================================================= */

async function loadStudentRanking() {

    const data =
        await loadJSON("student_ranking.json");

    if (!data) {
        return;
    }

    /*
       Supports:

       [
          {...},
          {...}
       ]

       and

       {
          "ranking": [...]
       }
    */

    let students = data;

    if (
        !Array.isArray(students) &&
        Array.isArray(data.ranking)
    ) {
        students = data.ranking;
    }

    if (!Array.isArray(students)) {
        return;
    }


    const cards =
        document.querySelectorAll(
            "#student-ranking .group-card"
        );

    if (!cards.length) {
        return;
    }


    /*
       Show top students in the group cards
       without destroying existing design.
    */

    const topStudents =
        students.slice(0, 3);


    topStudents.forEach(
        (student, index) => {

            const card = cards[index];

            if (!card) {
                return;
            }

            const title =
                card.querySelector("h3");

            const description =
                card.querySelector("p");

            if (title) {

                title.textContent =
                    safeText(
                        student.name
                    );
            }

            if (description) {

                description.textContent =
                    `Rank #${safeText(
                        student.rank || index + 1
                    )} · GPA ${
                        safeText(student.gpa)
                    }`;
            }

        }
    );
}


/* =========================================================
   INSTITUTION RANKING
========================================================= */

async function loadInstitutionRanking() {

    let data =
        await loadJSON(
            "institution_stats.json"
        );


    if (!data) {

        data =
            await loadJSON(
                "validated_institutions.json"
            );
    }


    if (!Array.isArray(data)) {
        return;
    }


    const rankingCard =
        document.querySelector(
            ".ranking-card"
        );

    if (!rankingCard) {
        return;
    }


    const rows =
        rankingCard.querySelectorAll(
            ".ranking-row"
        );


    data
        .slice(0, 3)
        .forEach(
            (institution, index) => {

                const row = rows[index];

                if (!row) {
                    return;
                }


                const rankInfo =
                    row.querySelector(
                        ".rank-info"
                    );

                const rankResult =
                    row.querySelector(
                        ".rank-result"
                    );

                const rankScore =
                    row.querySelector(
                        ".rank-score"
                    );


                const rankNumber =
                    row.querySelector(
                        ".rank-number"
                    );


                if (rankNumber) {

                    rankNumber.textContent =
                        String(
                            institution.rank ||
                            index + 1
                        ).padStart(
                            2,
                            "0"
                        );
                }


                if (rankInfo) {

                    const strong =
                        rankInfo.querySelector(
                            "strong"
                        );

                    const span =
                        rankInfo.querySelector(
                            "span"
                        );


                    if (strong) {

                        strong.textContent =
                            safeText(
                                institution.institute
                            );
                    }


                    if (span) {

                        span.textContent =
                            `Students: ${
                                formatNumber(
                                    institution.total_students
                                )
                            }`;
                    }
                }


                if (rankResult) {

                    const strong =
                        rankResult.querySelector(
                            "strong"
                        );

                    const span =
                        rankResult.querySelector(
                            "span"
                        );


                    if (strong) {

                        strong.textContent =
                            safeText(
                                institution.average_gpa
                            );
                    }


                    if (span) {

                        span.textContent =
                            "Average GPA";
                    }
                }


                if (rankScore) {

                    const strong =
                        rankScore.querySelector(
                            "strong"
                        );

                    const span =
                        rankScore.querySelector(
                            "span"
                        );


                    if (strong) {

                        strong.textContent =
                            safeText(
                                institution.gpa_5_count
                            );
                    }


                    if (span) {

                        span.textContent =
                            "GPA-5";
                    }
                }

            }
        );
}


/* =========================================================
   QUICK STATISTICS
========================================================= */

async function loadQuickStats() {

    const [
        studentsData,
        institutionsData,
        districtsData
    ] = await Promise.all([

        loadJSON(
            "students.json"
        ),

        loadJSON(
            "institution_stats.json"
        ),

        loadJSON(
            "district_ranking.json"
        )

    ]);


    const cards =
        document.querySelectorAll(
            ".quick-stats .stat-card"
        );


    if (!cards.length) {
        return;
    }


    /* Students */

    if (cards[2]) {

        const strong =
            cards[2].querySelector(
                "strong"
            );

        if (strong) {

            if (Array.isArray(
                studentsData
            )) {

                strong.textContent =
                    formatNumber(
                        studentsData.length
                    );

            }
        }
    }


    /* Institutions */

    if (cards[0]) {

        const strong =
            cards[0].querySelector(
                "strong"
            );

        if (strong) {

            if (Array.isArray(
                institutionsData
            )) {

                strong.textContent =
                    formatNumber(
                        institutionsData.length
                    );
            }
        }
    }


    /* Districts */

    if (cards[1]) {

        const strong =
            cards[1].querySelector(
                "strong"
            );

        if (strong) {

            if (Array.isArray(
                districtsData
            )) {

                strong.textContent =
                    formatNumber(
                        districtsData.length
                    );

            } else if (
                districtsData &&
                Array.isArray(
                    districtsData.ranking
                )
            ) {

                strong.textContent =
                    formatNumber(
                        districtsData.ranking.length
                    );
            }
        }
    }

}


/* =========================================================
   YEAR / BOARD DATA
========================================================= */

async function loadYearAndBoardData() {

    const [
        yearData,
        boardData
    ] = await Promise.all([

        loadJSON(
            "year_ranking.json"
        ),

        loadJSON(
            "board_ranking.json"
        )

    ]);


    console.log(
        "Year ranking loaded:",
        yearData
    );

    console.log(
        "Board ranking loaded:",
        boardData
    );

}


/* =========================================================
   INITIALIZE
========================================================= */

async function initializeRanking() {

    try {

        await Promise.all([

            loadStudentRanking(),

            loadInstitutionRanking(),

            loadQuickStats(),

            loadYearAndBoardData()

        ]);

        console.log(
            "✓ CTGBoardRanking data loaded"
        );

    } catch (error) {

        console.error(
            "Ranking initialization error:",
            error
        );

    }

}


/* =========================================================
   START
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    initializeRanking
);