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
   Automatically finds institution_results.json
========================================================= */

async function loadInstitutionRanking() {

    const rows = [
        document.getElementById("homeRank1"),
        document.getElementById("homeRank2"),
        document.getElementById("homeRank3")
    ];

    try {

        let response = null;

        /*
         * First try root folder
         */
        try {

            response = await fetch(
                "institution_results.json?v=" + Date.now(),
                {
                    cache: "no-store"
                }
            );

        } catch (e) {

            response = null;

        }


        /*
         * If root folder does not work,
         * try scraper folder
         */
        if (!response || !response.ok) {

            response = await fetch(
                "scraper/institution_results.json?v=" +
                Date.now(),
                {
                    cache: "no-store"
                }
            );

        }


        if (!response.ok) {

            throw new Error(
                "institution_results.json could not be loaded"
            );

        }


        const json =
            await response.json();


        /*
         * Support different JSON structures
         */

        let data = json;


        if (
            !Array.isArray(data) &&
            data &&
            Array.isArray(data.results)
        ) {

            data = data.results;

        }


        if (
            !Array.isArray(data) &&
            data &&
            Array.isArray(data.institutions)
        ) {

            data = data.institutions;

        }


        if (
            !Array.isArray(data) &&
            data &&
            Array.isArray(data.data)
        ) {

            data = data.data;

        }


        if (!Array.isArray(data)) {

            throw new Error(
                "Invalid institution_results.json format"
            );

        }


        /*
         * Convert data
         */

        let ranking = data.map(item => {

            const appeared =
                Number(
                    item.appeared || 0
                );


            const passed =
                Number(
                    item.passed || 0
                );


            let passingRate =
                Number(
                    item.passing_rate ||
                    item.pass_rate ||
                    item.passingRate ||
                    0
                );


            const gpa5 =
                Number(
                    item.gpa5 ||
                    item.gpa_5 ||
                    item.gpa5_count ||
                    0
                );


            /*
             * Calculate pass rate
             * if missing
             */

            if (
                passingRate === 0 &&
                appeared > 0
            ) {

                passingRate =
                    (
                        passed /
                        appeared
                    ) * 100;

            }


            return {

                eiin:
                    String(
                        item.eiin || ""
                    ).trim(),

                institution:
                    String(
                        item.institution_name ||
                        item.institution ||
                        item.name ||
                        ""
                    ).trim(),

                district:
                    String(
                        item.district ||
                        ""
                    ).trim(),

                appeared:
                    appeared,

                passed:
                    passed,

                passingRate:
                    passingRate,

                gpa5:
                    gpa5

            };

        });


        /*
         * Remove empty records
         */

        ranking =
            ranking.filter(
                item =>
                    item.institution
            );


        /*
         * Remove duplicate EIIN
         */

        const unique =
            new Map();


        ranking.forEach(item => {

            const key =
                item.eiin ||
                item.institution
                    .toLowerCase()
                    .trim();


            if (
                !unique.has(key)
            ) {

                unique.set(
                    key,
                    item
                );

            }

        });


        ranking =
            Array.from(
                unique.values()
            );


        /*
         * FINAL RANKING
         *
         * 1. GPA-5
         * 2. Passing Rate
         * 3. Passed
         * 4. Appeared
         */

        ranking.sort((a, b) => {

            if (
                b.gpa5 !==
                a.gpa5
            ) {

                return (
                    b.gpa5 -
                    a.gpa5
                );

            }


            if (
                b.passingRate !==
                a.passingRate
            ) {

                return (
                    b.passingRate -
                    a.passingRate
                );

            }


            if (
                b.passed !==
                a.passed
            ) {

                return (
                    b.passed -
                    a.passed
                );

            }


            if (
                b.appeared !==
                a.appeared
            ) {

                return (
                    b.appeared -
                    a.appeared
                );

            }


            return a.institution.localeCompare(
                b.institution
            );

        });


        console.log(
            "CTGBoardRanking TOP 3:",
            ranking.slice(0, 3)
        );


        /*
         * SHOW TOP 3
         */

        ranking
            .slice(0, 3)
            .forEach((item, index) => {

                const row =
                    rows[index];


                if (!row) {
                    return;
                }


                const name =
                    row.querySelector(
                        ".rank-info strong"
                    );


                const district =
                    row.querySelector(
                        ".rank-info span"
                    );


                const pass =
                    row.querySelector(
                        ".rank-result strong"
                    );


                const score =
                    row.querySelector(
                        ".rank-score strong"
                    );


                const passLabel =
                    row.querySelector(
                        ".rank-result span"
                    );


                const scoreLabel =
                    row.querySelector(
                        ".rank-score span"
                    );


                if (name) {

                    name.textContent =
                        item.institution;

                }


                if (district) {

                    district.textContent =
                        item.district ||
                        "Chattogram";

                }


                if (pass) {

                    pass.textContent =
                        item.passingRate
                            .toFixed(2) +
                        "%";

                }


                if (passLabel) {

                    passLabel.textContent =
                        "Pass Rate";

                }


                if (score) {

                    score.textContent =
                        item.gpa5
                            .toLocaleString(
                                "en-US"
                            );

                }


                if (scoreLabel) {

                    scoreLabel.textContent =
                        "GPA-5";

                }

            });


        /*
         * Clear unused rows
         */

        for (
            let i = ranking.length;
            i < 3;
            i++
        ) {

            const row =
                rows[i];


            if (!row) {
                continue;
            }


            const name =
                row.querySelector(
                    ".rank-info strong"
                );


            const district =
                row.querySelector(
                    ".rank-info span"
                );


            const pass =
                row.querySelector(
                    ".rank-result strong"
                );


            const score =
                row.querySelector(
                    ".rank-score strong"
                );


            if (name) {
                name.textContent = "—";
            }


            if (district) {
                district.textContent = "—";
            }


            if (pass) {
                pass.textContent = "—";
            }


            if (score) {
                score.textContent = "—";
            }

        }


    } catch (error) {

        console.error(
            "Institution ranking error:",
            error
        );


        rows.forEach(row => {

            if (!row) {
                return;
            }


            const name =
                row.querySelector(
                    ".rank-info strong"
                );


            const district =
                row.querySelector(
                    ".rank-info span"
                );


            if (name) {

                name.textContent =
                    "Data unavailable";

            }


            if (district) {

                district.textContent =
                    "Institution data unavailable";

            }

        });

    }

}

        /* =================================================
           NORMALIZE
        ================================================= */

        let institutions =
            data.map(
                item => {

                    const appeared =
                        Number(
                            item.appeared || 0
                        );


                    const passed =
                        Number(
                            item.passed || 0
                        );


                    let passingRate =
                        Number(
                            item.passing_rate || 0
                        );


                    const gpa5 =
                        Number(
                            item.gpa5 || 0
                        );


                    /*
                     * Calculate passing rate if necessary
                     */

                    if (
                        passingRate === 0 &&
                        appeared > 0
                    ) {

                        passingRate =
                            (
                                passed /
                                appeared
                            ) * 100;

                    }


                    return {

                        eiin:
                            String(
                                item.eiin || ""
                            ).trim(),

                        institution:
                            String(
                                item.institution_name ||
                                ""
                            ).trim(),

                        district:
                            String(
                                item.district ||
                                ""
                            ).trim(),

                        thana:
                            String(
                                item.thana ||
                                ""
                            ).trim(),

                        appeared:
                            appeared,

                        passed:
                            passed,

                        passingRate:
                            passingRate,

                        gpa5:
                            gpa5

                    };

                }
            )
            .filter(
                item =>
                    item.eiin &&
                    item.institution
            );


        /* =================================================
           REMOVE DUPLICATE EIIN
        ================================================= */

        const unique =
            new Map();


        institutions.forEach(
            item => {

                if (
                    !unique.has(
                        item.eiin
                    )
                ) {

                    unique.set(
                        item.eiin,
                        item
                    );

                }

            }
        );


        institutions =
            Array.from(
                unique.values()
            );


        /* =================================================
           FINAL RANKING
        ================================================= */

        institutions.sort(
            (a, b) => {

                /*
                 * 1 — GPA-5
                 */

                if (
                    b.gpa5 !==
                    a.gpa5
                ) {

                    return (
                        b.gpa5 -
                        a.gpa5
                    );

                }


                /*
                 * 2 — Passing Rate
                 */

                if (
                    b.passingRate !==
                    a.passingRate
                ) {

                    return (
                        b.passingRate -
                        a.passingRate
                    );

                }


                /*
                 * 3 — Passed
                 */

                if (
                    b.passed !==
                    a.passed
                ) {

                    return (
                        b.passed -
                        a.passed
                    );

                }


                /*
                 * 4 — Appeared
                 */

                if (
                    b.appeared !==
                    a.appeared
                ) {

                    return (
                        b.appeared -
                        a.appeared
                    );

                }


                /*
                 * Final tie breaker
                 */

                return a.institution.localeCompare(
                    b.institution
                );

            }
        );


        console.log(
            "FINAL TOP 10 INSTITUTIONS:",
            institutions.slice(
                0,
                10
            )
        );


        /* =================================================
           HOMEPAGE TOP 3
        ================================================= */

        const rows = [

            document.getElementById(
                "homeRank1"
            ),

            document.getElementById(
                "homeRank2"
            ),

            document.getElementById(
                "homeRank3"
            )

        ];


        institutions
            .slice(0, 3)
            .forEach(
                (institution, index) => {

                    const row =
                        rows[index];


                    if (!row) {
                        return;
                    }


                    const name =
                        row.querySelector(
                            ".rank-info strong"
                        );


                    const district =
                        row.querySelector(
                            ".rank-info span"
                        );


                    const pass =
                        row.querySelector(
                            ".rank-result strong"
                        );


                    const passLabel =
                        row.querySelector(
                            ".rank-result span"
                        );


                    const score =
                        row.querySelector(
                            ".rank-score strong"
                        );


                    const scoreLabel =
                        row.querySelector(
                            ".rank-score span"
                        );


                    /*
                     * Institution name
                     */

                    if (name) {

                        name.textContent =
                            institution.institution;

                    }


                    /*
                     * District
                     */

                    if (district) {

                        district.textContent =
                            institution.district ||
                            "Chattogram";

                    }


                    /*
                     * Passing Rate
                     */

                    if (pass) {

                        pass.textContent =
                            institution.passingRate
                                .toFixed(2) +
                            "%";

                    }


                    if (passLabel) {

                        passLabel.textContent =
                            "Pass Rate";

                    }


                    /*
                     * GPA-5
                     */

                    if (score) {

                        score.textContent =
                            institution.gpa5
                                .toLocaleString(
                                    "en-US"
                                );

                    }


                    if (scoreLabel) {

                        scoreLabel.textContent =
                            "GPA-5";

                    }


                    /*
                     * Rank number
                     */

                    const rankNumber =
                        row.querySelector(
                            ".rank-number"
                        );


                    if (rankNumber) {

                        rankNumber.textContent =
                            String(
                                index + 1
                            ).padStart(
                                2,
                                "0"
                            );

                    }

                }
            );


        /*
         * Clear unused rows
         */

        for (
            let i = institutions.length;
            i < 3;
            i++
        ) {

            const row =
                rows[i];


            if (!row) {
                continue;
            }


            const name =
                row.querySelector(
                    ".rank-info strong"
                );


            const district =
                row.querySelector(
                    ".rank-info span"
                );


            const pass =
                row.querySelector(
                    ".rank-result strong"
                );


            const score =
                row.querySelector(
                    ".rank-score strong"
                );


            if (name) {
                name.textContent = "—";
            }


            if (district) {
                district.textContent = "—";
            }


            if (pass) {
                pass.textContent = "—";
            }


            if (score) {
                score.textContent = "—";
            }

        }


    } catch (error) {

        console.error(
            "Institution ranking error:",
            error
        );

    }

}


/* =========================================================
   QUICK STATISTICS
   Uses institution_results.json
========================================================= */

async function loadQuickStats() {

    try {

        const response =
            await fetch(
                "institution_results.json?v=" +
                Date.now(),
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            return;
        }


        const json =
            await response.json();


        let institutions =
            json;


        if (
            !Array.isArray(institutions) &&
            json &&
            Array.isArray(json.results)
        ) {

            institutions =
                json.results;

        }


        if (
            !Array.isArray(institutions) &&
            json &&
            Array.isArray(json.institutions)
        ) {

            institutions =
                json.institutions;

        }


        if (!Array.isArray(institutions)) {
            return;
        }


        const uniqueInstitutions =
            new Set();


        const uniqueDistricts =
            new Set();


        let totalStudents = 0;


        institutions.forEach(
            item => {

                const eiin =
                    String(
                        item.eiin ||
                        ""
                    ).trim();


                const name =
                    String(
                        item.institution_name ||
                        ""
                    )
                    .trim()
                    .toLowerCase();


                const district =
                    String(
                        item.district ||
                        ""
                    )
                    .trim()
                    .toLowerCase();


                if (eiin) {

                    uniqueInstitutions.add(
                        eiin
                    );

                }
                else if (name) {

                    uniqueInstitutions.add(
                        name
                    );

                }


                if (district) {

                    uniqueDistricts.add(
                        district
                    );

                }


                totalStudents +=
                    Number(
                        item.appeared || 0
                    );

            }
        );


        const statInstitutions =
            document.getElementById(
                "statInstitutions"
            );


        const statDistricts =
            document.getElementById(
                "statDistricts"
            );


        const statStudents =
            document.getElementById(
                "statStudents"
            );


        if (statInstitutions) {

            statInstitutions.textContent =
                uniqueInstitutions
                    .size
                    .toLocaleString(
                        "en-US"
                    );

        }


        if (statDistricts) {

            statDistricts.textContent =
                uniqueDistricts
                    .size
                    .toLocaleString(
                        "en-US"
                    );

        }


        if (statStudents) {

            statStudents.textContent =
                totalStudents
                    .toLocaleString(
                        "en-US"
                    );

        }


    } catch (error) {

        console.error(
            "Quick stats error:",
            error
        );

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


/* =========================================================
   TOTAL VISITS
========================================================= */

async function loadTotalVisits() {

    const visitElement =
        document.getElementById(
            "totalVisits"
        );


    if (!visitElement) {
        return;
    }


    try {

        const response =
            await fetch(
                "https://ymwhodckmbybccufzjot.supabase.co/rest/v1/site_stats?id=eq.1&select=total_visits",
                {
                    headers: {

                        "apikey":
                            "তোমার_SUPABASE_PUBLISHABLE_KEY",

                        "Authorization":
                            "Bearer তোমার_SUPABASE_PUBLISHABLE_KEY"

                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                "Visit API Error: " +
                response.status
            );

        }


        const data =
            await response.json();


        if (
            Array.isArray(data) &&
            data.length > 0
        ) {

            visitElement.textContent =
                Number(
                    data[0].total_visits
                )
                .toLocaleString(
                    "en-US"
                );

        }


    } catch (error) {

        console.error(
            "Total visits load error:",
            error
        );

    }

}


/* =========================================================
   START TOTAL VISITS
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    loadTotalVisits
);