/* =========================================================
   CTGBoardRanking — MAIN SCRIPT
========================================================= */

"use strict";


/* =========================================================
   DATA PATH
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

    const n =
        Number(
            String(value)
                .replace(/,/g, "")
                .replace(/%/g, "")
                .trim()
        );

    return Number.isFinite(n)
        ? n
        : 0;

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
     * Supported JSON formats:
     *
     * [
     *   {...}
     * ]
     *
     * OR
     *
     * {
     *   institutions: [...]
     * }
     *
     * OR
     *
     * {
     *   results: [...]
     * }
     *
     * OR
     *
     * {
     *   data: [...]
     * }
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
   NORMALIZE INSTITUTION
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


    /*
     * Calculate pass rate if missing
     */

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
   REMOVE DUPLICATE INSTITUTIONS
========================================================= */

function uniqueInstitutions(data) {

    const map =
        new Map();


    data.forEach(raw => {

        const item =
            normalize(raw);


        /*
         * Ignore records without institution name
         */

        if (!item.name) {

            return;

        }


        /*
         * Prefer EIIN as unique key.
         * Otherwise use institution name.
         */

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
     * Ranking priority:
     *
     * 1. GPA-5
     * 2. Pass Rate
     * 3. Passed
     * 4. Appeared
     */

    institutions.sort(
        (a, b) => {

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
                b.passRate !==
                a.passRate
            ) {

                return (
                    b.passRate -
                    a.passRate
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


            return (
                b.appeared -
                a.appeared
            );

        }
    );


    const top3 =
        institutions.slice(
            0,
            3
        );


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
     *
     * IMPORTANT:
     * Student total is NO LONGER calculated
     * from institution_results.json.
     *
     * It is loaded directly from Supabase
     * using loadStudentTotal().
     */

    const studentElement =
        document.getElementById(
            "statStudents"
        );


    if (studentElement) {

        studentElement.textContent =
            "Loading...";

    }


    console.log(
        "Institution total:",
        institutions.length
    );


    console.log(
        "District total:",
        districtSet.size
    );

}


/* =========================================================
   LOAD ACTUAL STUDENT TOTAL FROM SUPABASE
========================================================= */

async function loadStudentTotal() {

    const element =
        document.getElementById(
            "statStudents"
        );


    if (!element) {

        console.warn(
            "statStudents element not found"
        );

        return;

    }


    /*
     * Make sure Supabase client exists
     */

    if (
        typeof supabase ===
        "undefined"
    ) {

        console.error(
            "Supabase client is not available."
        );

        element.textContent =
            "Error";

        return;

    }


    console.log(
        "Loading actual student total from Supabase..."
    );


    try {

        /*
         * IMPORTANT:
         *
         * head: true
         * means we only request the COUNT,
         * not all student records.
         *
         * count: "exact"
         * gives the exact number of rows.
         */

        const {
            count,
            error
        } =
            await supabase
                .from("students")
                .select(
                    "*",
                    {
                        count: "exact",
                        head: true
                    }
                );


        if (error) {

            throw error;

        }


        const total =
            Number(count || 0);


        element.textContent =
            total.toLocaleString(
                "en-US"
            );


        console.log(
            "✓ Actual Student Total:",
            total
        );


    } catch (error) {

        console.error(
            "❌ Student count error:",
            error
        );


        element.textContent =
            "Unavailable";

    }

}


/* =========================================================
   TOTAL VISITS
========================================================= */

async function loadTotalVisits() {

    const element =
        document.getElementById(
            "totalVisits"
        );


    if (!element) {

        console.warn(
            "totalVisits element not found"
        );

        return;

    }


    console.log(
        "Loading total visits..."
    );


    try {

        const response =
            await fetch(
                "/api/visits",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    cache: "no-store"
                }
            );


        console.log(
            "Visit API status:",
            response.status
        );


        if (!response.ok) {

            const errorText =
                await response.text();


            console.error(
                "Visit API error:",
                errorText
            );


            return;

        }


        const data =
            await response.json();


        console.log(
            "Visit API response:",
            data
        );


        if (
            data &&
            typeof data.total !==
            "undefined"
        ) {

            element.textContent =
                Number(data.total)
                    .toLocaleString(
                        "en-US"
                    );

        }

    } catch (error) {

        console.error(
            "Total visits error:",
            error
        );

    }

}


/* =========================================================
   INITIALIZE TOTAL VISITS
========================================================= */

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        loadTotalVisits
    );

} else {

    loadTotalVisits();

}


/* =========================================================
   MAIN INITIALIZE
========================================================= */

async function initialize() {

    /*
     * DARK MODE
     */

    initDarkMode();


    /*
     * LOAD ACTUAL STUDENT COUNT
     *
     * This is independent of the
     * institution JSON.
     */

    loadStudentTotal();


    try {

        /*
         * LOAD INSTITUTION JSON
         */

        const raw =
            await getInstitutions();


        console.log(
            "✓ JSON records:",
            raw.length
        );


        /*
         * REMOVE DUPLICATES
         */

        const institutions =
            uniqueInstitutions(
                raw
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
         * TOP 3 INSTITUTIONS
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
         * Only show ranking error
         * when institution JSON fails.
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
     * Visit counter is independent.
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