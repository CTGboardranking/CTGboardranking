/* =========================================================
   CTGBoardRanking — MAIN SCRIPT
========================================================= */

"use strict";


/* =========================================================
   DATA PATH — CORRECT PATH
========================================================= */

const INSTITUTION_JSON =
    "institution-collector/institution_results.json";


/* =========================================================
   DARK MODE
========================================================= */

function initDarkMode() {

    const themeBtn =
        document.getElementById("themeBtn");

    const savedTheme =
        localStorage.getItem("ctg-theme");

    if (savedTheme === "dark") {
        document.body.classList.add("dark");
    }

    if (themeBtn) {

        themeBtn.addEventListener("click", () => {

            document.body.classList.toggle("dark");

            localStorage.setItem(
                "ctg-theme",
                document.body.classList.contains("dark")
                    ? "dark"
                    : "light"
            );

        });

    }

}


/* =========================================================
   NUMBER
========================================================= */

function num(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return 0;
    }

    const n = Number(
        String(value)
            .replace(/,/g, "")
            .replace(/%/g, "")
            .trim()
    );

    return Number.isFinite(n) ? n : 0;

}


/* =========================================================
   LOAD INSTITUTION JSON
========================================================= */

async function getInstitutions() {

    const url =
        INSTITUTION_JSON +
        "?v=" +
        Date.now();


    console.log(
        "Loading:",
        url
    );


    const response =
        await fetch(
            url,
            {
                cache: "no-store"
            }
        );


    if (!response.ok) {

        throw new Error(
            "JSON HTTP " +
            response.status +
            " — " +
            url
        );

    }


    const data =
        await response.json();


    /*
     * Your JSON is a direct array:
     *
     * [
     *   {
     *     eiin: "...",
     *     institution_name: "...",
     *     district: "...",
     *     appeared: 83,
     *     passed: 54,
     *     passing_rate: 65.06,
     *     gpa5: 2
     *   }
     * ]
     */

    if (Array.isArray(data)) {

        return data;

    }


    if (
        data &&
        Array.isArray(data.institutions)
    ) {

        return data.institutions;

    }


    if (
        data &&
        Array.isArray(data.results)
    ) {

        return data.results;

    }


    if (
        data &&
        Array.isArray(data.data)
    ) {

        return data.data;

    }


    throw new Error(
        "Invalid institution_results.json format"
    );

}


/* =========================================================
   NORMALIZE
========================================================= */

function normalize(item) {

    const appeared =
        num(item.appeared);


    const passed =
        num(item.passed);


    let passRate =
        num(item.passing_rate);


    const gpa5 =
        num(item.gpa5);


    if (
        passRate === 0 &&
        appeared > 0
    ) {

        passRate =
            (passed / appeared) * 100;

    }


    return {

        eiin:
            String(
                item.eiin || ""
            ).trim(),

        name:
            String(
                item.institution_name ||
                item.institution ||
                item.institute ||
                item.name ||
                ""
            ).trim(),

        district:
            String(
                item.district || ""
            ).trim(),

        thana:
            String(
                item.thana || ""
            ).trim(),

        appeared,

        passed,

        passRate,

        gpa5

    };

}


/* =========================================================
   REMOVE DUPLICATES
========================================================= */

function uniqueInstitutions(data) {

    const map = new Map();


    data.forEach(raw => {

        const item =
            normalize(raw);


        if (!item.name) {
            return;
        }


        const key =
            item.eiin ||
            item.name.toLowerCase();


        if (!map.has(key)) {

            map.set(
                key,
                item
            );

        }

    });


    return Array.from(
        map.values()
    );

}


/* =========================================================
   TOP 3 INSTITUTIONS
========================================================= */

function showTopInstitutions(
    institutions
) {

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


    /*
     * Ranking:
     * GPA-5
     * Pass Rate
     * Passed
     * Appeared
     */

    institutions.sort(
        (a, b) => {

            if (b.gpa5 !== a.gpa5) {

                return b.gpa5 - a.gpa5;

            }


            if (
                b.passRate !==
                a.passRate
            ) {

                return (
                    b.passRate -
                    a.passRate
                );

            }


            if (b.passed !== a.passed) {

                return b.passed - a.passed;

            }


            return b.appeared - a.appeared;

        }
    );


    const top3 =
        institutions.slice(0, 3);


    console.log(
        "TOP 3 INSTITUTIONS:",
        top3
    );


    top3.forEach(
        (item, index) => {

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


            if (name) {

                name.textContent =
                    item.name;

            }


            if (district) {

                district.textContent =
                    item.district ||
                    "Chattogram";

            }


            if (pass) {

                pass.textContent =
                    item.passRate.toFixed(2) +
                    "%";

            }


            if (passLabel) {

                passLabel.textContent =
                    "Pass Rate";

            }


            if (score) {

                score.textContent =
                    item.gpa5.toLocaleString(
                        "en-US"
                    );

            }


            if (scoreLabel) {

                scoreLabel.textContent =
                    "GPA-5";

            }

        }
    );

}


/* =========================================================
   QUICK STATS
========================================================= */

function showStatistics(
    institutions
) {

    /*
     * INSTITUTION TOTAL
     */

    const institutionElement =
        document.getElementById(
            "statInstitutions"
        );


    if (institutionElement) {

        institutionElement.textContent =
            institutions.length.toLocaleString(
                "en-US"
            );

    }


    /*
     * DISTRICT TOTAL
     */

    const districtSet =
        new Set();


    institutions.forEach(item => {

        if (item.district) {

            districtSet.add(
                item.district
                    .trim()
                    .toUpperCase()
            );

        }

    });


    const districtElement =
        document.getElementById(
            "statDistricts"
        );


    if (districtElement) {

        districtElement.textContent =
            districtSet.size.toLocaleString(
                "en-US"
            );

    }


    /*
     * STUDENT TOTAL
     */

    let totalStudents = 0;


    institutions.forEach(item => {

        totalStudents +=
            num(item.appeared);

    });


    const studentElement =
        document.getElementById(
            "statStudents"
        );


    if (studentElement) {

        studentElement.textContent =
            totalStudents.toLocaleString(
                "en-US"
            );

    }


    console.log(
        "Institution total:",
        institutions.length
    );


    console.log(
        "District total:",
        districtSet.size
    );


    console.log(
        "Student total:",
        totalStudents
    );

}


/* =====================================================
   TOTAL VISITS
===================================================== */

async function loadTotalVisits() {

    const element =
        document.getElementById("totalVisits");

    if (!element) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/visits",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    }
                }
            );

        if (!response.ok) {

            console.warn(
                "Visit counter failed:",
                response.status
            );

            return;
        }

        const data =
            await response.json();

        if (
            data &&
            typeof data.total !== "undefined"
        ) {

            element.textContent =
                Number(
                    data.total
                ).toLocaleString("en-US");

        }

    } catch (error) {

        console.warn(
            "Total visits error:",
            error
        );

    }
}


/* Run once when page loads */

document.addEventListener(
    "DOMContentLoaded",
    loadTotalVisits
);

/* =========================================================
   MAIN
========================================================= */

async function initialize() {

    initDarkMode();


    try {

        const raw =
            await getInstitutions();


        const institutions =
            uniqueInstitutions(raw);


        console.log(
            "✓ JSON records:",
            raw.length
        );


        console.log(
            "✓ Unique institutions:",
            institutions.length
        );


        /*
         * QUICK STATS
         */

        showStatistics(
            institutions
        );


        /*
         * TOP 3
         */

        showTopInstitutions(
            institutions
        );


        console.log(
            "✓ HOMEPAGE DATA LOADED"
        );

    }

    catch (error) {

        console.error(
            "❌ DATA LOADING ERROR:",
            error
        );


        /*
         * Only show error if the JSON
         * genuinely cannot be loaded.
         */

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
                    "Check JSON path";

            }

        });

    }


    /*
     * Independent of ranking.
     */

    loadTotalVisits();

}


/* =========================================================
   START
========================================================= */

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initialize
    );

} else {

    initialize();

}