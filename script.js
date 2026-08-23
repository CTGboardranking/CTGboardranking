/* =========================================================
   CTGBoardRanking — MAIN SCRIPT
   Homepage Data Loader
========================================================= */

"use strict";


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

            const isDark =
                document.body.classList.contains("dark");

            localStorage.setItem(
                "ctg-theme",
                isDark ? "dark" : "light"
            );

        });

    }

}


/* =========================================================
   NUMBER HELPER
========================================================= */

function toNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return 0;
    }

    const cleaned =
        String(value)
            .replace(/,/g, "")
            .replace(/%/g, "")
            .trim();

    const n = Number(cleaned);

    return Number.isFinite(n)
        ? n
        : 0;

}


/* =========================================================
   LOAD INSTITUTION JSON
========================================================= */

async function loadInstitutionResults() {

    const paths = [

        "./institution_results.json",

        "./scraper/institution_results.json",

        "institution_results.json",

        "scraper/institution_results.json"

    ];


    let lastError = null;


    for (const path of paths) {

        try {

            console.log(
                "Trying JSON:",
                path
            );


            const response =
                await fetch(
                    path + "?v=" + Date.now(),
                    {
                        cache: "no-store"
                    }
                );


            if (!response.ok) {

                lastError =
                    new Error(
                        path +
                        " HTTP " +
                        response.status
                    );

                continue;

            }


            const json =
                await response.json();


            let data = null;


            /* Direct array */

            if (
                Array.isArray(json)
            ) {

                data = json;

            }


            /* { institutions: [] } */

            else if (
                json &&
                Array.isArray(
                    json.institutions
                )
            ) {

                data =
                    json.institutions;

            }


            /* { results: [] } */

            else if (
                json &&
                Array.isArray(
                    json.results
                )
            ) {

                data =
                    json.results;

            }


            /* { data: [] } */

            else if (
                json &&
                Array.isArray(
                    json.data
                )
            ) {

                data =
                    json.data;

            }


            if (
                Array.isArray(data) &&
                data.length > 0
            ) {

                console.log(
                    "✓ Institution JSON loaded:",
                    path,
                    data.length
                );

                return data;

            }

        }

        catch (error) {

            lastError = error;

            console.warn(
                "JSON load failed:",
                path,
                error
            );

        }

    }


    throw (
        lastError ||
        new Error(
            "institution_results.json not found"
        )
    );

}


/* =========================================================
   NORMALIZE DATA
========================================================= */

function normalizeInstitution(item) {

    const appeared =
        toNumber(
            item.appeared ??
            item.total_students ??
            item.total_appeared ??
            item.students
        );


    const passed =
        toNumber(
            item.passed ??
            item.total_passed
        );


    let passingRate =
        toNumber(
            item.passing_rate ??
            item.passingRate ??
            item.pass_rate
        );


    const gpa5 =
        toNumber(
            item.gpa5 ??
            item.gpa_5 ??
            item.gpa5_count ??
            item.gpa_5_count ??
            item.total_gpa5
        );


    /* Calculate pass rate if JSON doesn't have it */

    if (
        passingRate === 0 &&
        appeared > 0
    ) {

        passingRate =
            (passed / appeared) * 100;

    }


    return {

        eiin:
            String(
                item.eiin ?? ""
            ).trim(),

        institution:
            String(
                item.institution_name ??
                item.institution ??
                item.institute ??
                item.name ??
                ""
            ).trim(),

        district:
            String(
                item.district ?? ""
            ).trim(),

        thana:
            String(
                item.thana ??
                item.upazila ??
                ""
            ).trim(),

        appeared,

        passed,

        passingRate,

        gpa5

    };

}


/* =========================================================
   UNIQUE INSTITUTIONS
========================================================= */

function makeUniqueInstitutions(data) {

    const map = new Map();


    data.forEach(raw => {

        const item =
            normalizeInstitution(raw);


        if (
            !item.institution
        ) {
            return;
        }


        const key =
            item.eiin ||
            item.institution
                .toLowerCase()
                .trim();


        /*
         * If same EIIN appears more than once,
         * keep the record with the larger appeared count.
         */

        if (!map.has(key)) {

            map.set(
                key,
                item
            );

        }

        else {

            const old =
                map.get(key);


            if (
                item.appeared >
                old.appeared
            ) {

                map.set(
                    key,
                    item
                );

            }

        }

    });


    return Array.from(
        map.values()
    );

}


/* =========================================================
   INSTITUTION RANKING
========================================================= */

async function loadHomepageInstitutionRanking(
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


    if (
        !rows.some(Boolean)
    ) {

        console.warn(
            "Homepage ranking rows not found."
        );

        return;

    }


    /*
     * Ranking order:
     *
     * 1. GPA-5
     * 2. Passing Rate
     * 3. Passed
     * 4. Appeared
     */

    const ranking =
        [...institutions].sort(
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


                return a.institution
                    .localeCompare(
                        b.institution
                    );

            }
        );


    const top3 =
        ranking.slice(0, 3);


    console.log(
        "Institution Total:",
        institutions.length
    );

    console.log(
        "TOP 3:",
        top3
    );


    /*
     * Put TOP 3 into homepage
     */

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


            /* Institution name */

            if (name) {

                name.textContent =
                    item.institution;

            }


            /* District */

            if (district) {

                district.textContent =
                    item.district ||
                    "Chattogram";

            }


            /* Pass rate */

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


            /* GPA-5 */

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

        }
    );


    /*
     * If less than 3 records,
     * clear remaining rows.
     */

    for (
        let i = top3.length;
        i < rows.length;
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

}


/* =========================================================
   QUICK STATISTICS
========================================================= */

function loadHomepageStatistics(
    institutions
) {

    const institutionElement =
        document.getElementById(
            "statInstitutions"
        );


    const districtElement =
        document.getElementById(
            "statDistricts"
        );


    const studentElement =
        document.getElementById(
            "statStudents"
        );


    /*
     * Institution total
     */

    if (institutionElement) {

        institutionElement.textContent =
            institutions.length
                .toLocaleString(
                    "en-US"
                );

    }


    /*
     * District total
     */

    const districtSet =
        new Set();


    institutions.forEach(
        item => {

            const district =
                String(
                    item.district || ""
                )
                .trim()
                .toUpperCase();


            if (district) {

                districtSet.add(
                    district
                );

            }

        }
    );


    if (districtElement) {

        districtElement.textContent =
            districtSet.size
                .toLocaleString(
                    "en-US"
                );

    }


    /*
     * Student total
     *
     * Sum of appeared students
     */

    const totalStudents =
        institutions.reduce(
            (total, item) => {

                return (
                    total +
                    toNumber(
                        item.appeared
                    )
                );

            },
            0
        );


    if (studentElement) {

        studentElement.textContent =
            totalStudents
                .toLocaleString(
                    "en-US"
                );

    }


    console.log(
        "Homepage Statistics:",
        {
            institutions:
                institutions.length,

            districts:
                districtSet.size,

            students:
                totalStudents
        }
    );

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
        return;
    }


    /*
     * Do not break the rest of the homepage
     * if Supabase key is not configured.
     */

    const SUPABASE_URL =
        "https://ymwhodckmbybccufzjot.supabase.co";


    const SUPABASE_KEY =
        "তোমার_SUPABASE_PUBLISHABLE_KEY";


    if (
        !SUPABASE_KEY ||
        SUPABASE_KEY ===
        "তোমার_SUPABASE_PUBLISHABLE_KEY"
    ) {

        console.warn(
            "Supabase publishable key is not configured."
        );

        return;

    }


    try {

        const response =
            await fetch(
                SUPABASE_URL +
                "/rest/v1/site_stats?id=eq.1&select=total_visits",
                {

                    method: "GET",

                    headers: {

                        "apikey":
                            SUPABASE_KEY,

                        "Authorization":
                            "Bearer " +
                            SUPABASE_KEY

                    }

                }
            );


        if (!response.ok) {

            throw new Error(
                "Supabase HTTP " +
                response.status
            );

        }


        const data =
            await response.json();


        if (
            Array.isArray(data) &&
            data.length > 0
        ) {

            element.textContent =
                toNumber(
                    data[0].total_visits
                ).toLocaleString(
                    "en-US"
                );

        }

    }

    catch (error) {

        console.error(
            "Total visits error:",
            error
        );

    }

}


/* =========================================================
   MAIN INITIALIZATION
========================================================= */

async function initializeHomepage() {

    console.log(
        "===================================="
    );

    console.log(
        "CTGBoardRanking initializing..."
    );


    initDarkMode();


    try {

        /*
         * Load JSON ONCE
         */

        const rawData =
            await loadInstitutionResults();


        /*
         * Normalize + remove duplicates
         */

        const institutions =
            makeUniqueInstitutions(
                rawData
            );


        console.log(
            "✓ Raw records:",
            rawData.length
        );


        console.log(
            "✓ Unique institutions:",
            institutions.length
        );


        /*
         * Homepage statistics
         */

        loadHomepageStatistics(
            institutions
        );


        /*
         * Homepage TOP 3
         */

        await loadHomepageInstitutionRanking(
            institutions
        );


        console.log(
            "✓ Institution data loaded successfully"
        );

    }

    catch (error) {

        console.error(
            "❌ Homepage data loading error:",
            error
        );


        /*
         * Show error only if JSON really
         * cannot be loaded.
         */

        const institutionElement =
            document.getElementById(
                "statInstitutions"
            );


        const districtElement =
            document.getElementById(
                "statDistricts"
            );


        const studentElement =
            document.getElementById(
                "statStudents"
            );


        if (institutionElement) {
            institutionElement.textContent = "—";
        }


        if (districtElement) {
            districtElement.textContent = "—";
        }


        if (studentElement) {
            studentElement.textContent = "—";
        }


        /*
         * Top 3 error display
         */

        [
            "homeRank1",
            "homeRank2",
            "homeRank3"
        ]
        .forEach(id => {

            const row =
                document.getElementById(id);


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
                    "JSON loading failed";

            }

        });

    }


    /*
     * Total visits is independent.
     * Even if it fails, ranking still works.
     */

    loadTotalVisits();


    console.log(
        "CTGBoardRanking initialization complete."
    );

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
        initializeHomepage
    );

}

else {

    initializeHomepage();

}