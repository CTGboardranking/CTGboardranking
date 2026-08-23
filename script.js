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
   DATA FILE
   institution_results.json MUST be used
========================================================= */

const INSTITUTION_RESULTS_FILE =
    "institution_results.json";


/* =========================================================
   LOAD JSON
========================================================= */

async function loadInstitutionResults() {

    const paths = [

        "institution_results.json",

        "scraper/institution_results.json"

    ];

    for (const path of paths) {

        try {

            const response = await fetch(
                path + "?v=" + Date.now(),
                {
                    cache: "no-store"
                }
            );

            if (!response.ok) {
                continue;
            }

            const data = await response.json();

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

        } catch (error) {

            console.warn(
                "Could not load:",
                path,
                error
            );

        }

    }

    throw new Error(
        "institution_results.json could not be loaded"
    );

}


/* =========================================================
   NUMBER
========================================================= */

function number(value) {

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

    return Number.isFinite(n)
        ? n
        : 0;

}


/* =========================================================
   NORMALIZE INSTITUTION
========================================================= */

function normalizeInstitution(item) {

    const appeared =
        number(
            item.appeared ??
            item.total_students ??
            item.total_appeared
        );


    const passed =
        number(
            item.passed ??
            item.total_passed
        );


    let passingRate =
        number(
            item.passing_rate ??
            item.pass_rate ??
            item.passingRate
        );


    const gpa5 =
        number(
            item.gpa5 ??
            item.gpa_5 ??
            item.total_gpa5 ??
            item.gpa5_count ??
            item.gpa_5_count
        );


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
   CREATE UNIQUE INSTITUTION LIST
========================================================= */

function uniqueInstitutions(data) {

    const map = new Map();

    for (const raw of data) {

        const item =
            normalizeInstitution(raw);

        if (!item.institution) {
            continue;
        }

        const key =
            item.eiin ||
            item.institution
                .toLowerCase()
                .trim();

        /*
         * If duplicate EIIN exists,
         * keep the record with the larger appeared value.
         */

        if (!map.has(key)) {

            map.set(
                key,
                item
            );

        } else {

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

    }

    return Array.from(
        map.values()
    );

}


/* =========================================================
   INSTITUTION RANKING
========================================================= */

async function loadInstitutionRanking() {

    const rows = [

        document.getElementById("homeRank1"),

        document.getElementById("homeRank2"),

        document.getElementById("homeRank3")

    ];


    if (!rows.some(Boolean)) {
        return;
    }


    try {

        const data =
            await loadInstitutionResults();


        const institutions =
            uniqueInstitutions(data);


        /*
         * TOP INSTITUTION RANKING
         *
         * 1. GPA-5
         * 2. Passing Rate
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

            }
        );


        const top3 =
            institutions.slice(0, 3);


        console.log(
            "Institution total:",
            institutions.length
        );


        console.log(
            "TOP 3:",
            top3
        );


        /*
         * Display TOP 3
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
                        item.passingRate.toFixed(2) +
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


        /*
         * Clear unused rows
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


            const elements =
                row.querySelectorAll(
                    ".rank-info strong, .rank-info span, .rank-result strong, .rank-score strong"
                );


            elements.forEach(
                element => {
                    element.textContent = "—";
                }
            );

        }


    } catch (error) {

        console.error(
            "Institution ranking error:",
            error
        );


        rows.forEach(
            row => {

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
                        "institution_results.json";

                }

            }
        );

    }

}


/* =========================================================
   QUICK STATS
========================================================= */

async function loadQuickStats() {

    try {

        const data =
            await loadInstitutionResults();


        const institutions =
            uniqueInstitutions(data);


        const districts =
            new Set();


        let totalStudents = 0;


        /*
         * Calculate from institution_results.json
         */

        institutions.forEach(
            item => {

                if (
                    item.district
                ) {

                    districts.add(
                        item.district
                            .toLowerCase()
                            .trim()
                    );

                }


                totalStudents +=
                    item.appeared;

            }
        );


        /*
         * Institution total
         */

        const statInstitutions =
            document.getElementById(
                "statInstitutions"
            );


        if (statInstitutions) {

            statInstitutions.textContent =
                institutions.length.toLocaleString(
                    "en-US"
                );

        }


        /*
         * District total
         */

        const statDistricts =
            document.getElementById(
                "statDistricts"
            );


        if (statDistricts) {

            statDistricts.textContent =
                districts.size.toLocaleString(
                    "en-US"
                );

        }


        /*
         * Student total
         */

        const statStudents =
            document.getElementById(
                "statStudents"
            );


        if (statStudents) {

            statStudents.textContent =
                totalStudents.toLocaleString(
                    "en-US"
                );

        }


        console.log(
            "Institution Total:",
            institutions.length
        );


        console.log(
            "Student Total:",
            totalStudents
        );


        console.log(
            "District Total:",
            districts.size
        );


    } catch (error) {

        console.error(
            "Quick stats error:",
            error
        );

    }

}


/* =========================================================
   STUDENT RANKING
========================================================= */

async function loadStudentRanking() {

    try {

        const response =
            await fetch(
                "student_results.json?v=" +
                Date.now(),
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        const students =
            Array.isArray(data)
                ? data
                : (
                    data &&
                    Array.isArray(
                        data.results
                    )
                        ? data.results
                        : []
                );


        console.log(
            "Student results:",
            students.length
        );


    } catch (error) {

        console.warn(
            "Student ranking not loaded:",
            error
        );

    }

}


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

        /*
         * IMPORTANT:
         * Replace the key below with your
         * actual Supabase publishable key.
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

            return;

        }


        const response =
            await fetch(
                SUPABASE_URL +
                "/rest/v1/site_stats?id=eq.1&select=total_visits",
                {

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
                "HTTP " +
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
                ).toLocaleString(
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
   INITIALIZE
========================================================= */

async function initializeRanking() {

    await Promise.all([

        loadInstitutionRanking(),

        loadQuickStats(),

        loadStudentRanking(),

        loadTotalVisits()

    ]);


    console.log(
        "✓ CTGBoardRanking loaded successfully"
    );

}


/* =========================================================
   START
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    initializeRanking
);