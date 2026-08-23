/* =========================================================
   CTGBoardRanking — Main Script
   Homepage Data Loader
========================================================= */

"use strict";


/* =========================================================
   DARK MODE
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const themeBtn =
        document.getElementById("themeBtn");

    const savedTheme =
        localStorage.getItem("ctg-theme");

    if (savedTheme === "dark") {
        document.body.classList.add("dark");
    }

    if (themeBtn) {

        themeBtn.addEventListener("click", function () {

            document.body.classList.toggle("dark");

            const dark =
                document.body.classList.contains("dark");

            localStorage.setItem(
                "ctg-theme",
                dark ? "dark" : "light"
            );

        });

    }

});


/* =========================================================
   INSTITUTION JSON
========================================================= */

const INSTITUTION_JSON_PATHS = [

    "institution_results.json",

    "scraper/institution_results.json"

];


/* =========================================================
   LOAD INSTITUTION RESULTS
========================================================= */

async function loadInstitutionResults() {

    for (
        const path
        of INSTITUTION_JSON_PATHS
    ) {

        try {

            const response =
                await fetch(
                    path + "?v=" + Date.now(),
                    {
                        cache: "no-store"
                    }
                );

            if (!response.ok) {
                continue;
            }

            const json =
                await response.json();


            /* JSON is directly an array */

            if (
                Array.isArray(json)
            ) {

                return json;

            }


            /* JSON object */

            if (
                json &&
                Array.isArray(
                    json.institutions
                )
            ) {

                return json.institutions;

            }


            if (
                json &&
                Array.isArray(
                    json.results
                )
            ) {

                return json.results;

            }


            if (
                json &&
                Array.isArray(
                    json.data
                )
            ) {

                return json.data;

            }

        }
        catch (error) {

            console.warn(
                "JSON load failed:",
                path,
                error
            );

        }

    }


    throw new Error(
        "institution_results.json not found"
    );

}


/* =========================================================
   NUMBER
========================================================= */

function toNumber(value) {

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
   NORMALIZE
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


    const gpa5 =
        toNumber(
            item.gpa5 ??
            item.gpa_5 ??
            item.total_gpa5 ??
            item.gpa5_count ??
            item.gpa_5_count
        );


    let passingRate =
        toNumber(
            item.passing_rate ??
            item.pass_rate ??
            item.passingRate
        );


    if (
        passingRate === 0 &&
        appeared > 0 &&
        passed >= 0
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
                item.district ??
                ""
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

function createUniqueInstitutions(data) {

    const map =
        new Map();


    data.forEach(function (raw) {

        const item =
            normalizeInstitution(raw);


        if (!item.institution) {
            return;
        }


        const key =
            item.eiin ||
            item.institution
                .toLowerCase()
                .trim();


        if (!map.has(key)) {

            map.set(
                key,
                item
            );

            return;

        }


        /*
         * Duplicate EIIN:
         * keep the record with larger
         * student count.
         */

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

    });


    return Array.from(
        map.values()
    );

}


/* =========================================================
   RANKING
========================================================= */

function sortInstitutions(institutions) {

    return institutions.sort(
        function (a, b) {


            /* 1. GPA-5 */

            if (
                b.gpa5 !==
                a.gpa5
            ) {

                return (
                    b.gpa5 -
                    a.gpa5
                );

            }


            /* 2. Passing rate */

            if (
                b.passingRate !==
                a.passingRate
            ) {

                return (
                    b.passingRate -
                    a.passingRate
                );

            }


            /* 3. Passed */

            if (
                b.passed !==
                a.passed
            ) {

                return (
                    b.passed -
                    a.passed
                );

            }


            /* 4. Appeared */

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

}


/* =========================================================
   HOMEPAGE TOP 3
========================================================= */

async function loadHomepageTop3() {

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


    try {

        const data =
            await loadInstitutionResults();


        const institutions =
            createUniqueInstitutions(
                data
            );


        const ranking =
            sortInstitutions(
                institutions
            );


        const top3 =
            ranking.slice(
                0,
                3
            );


        console.log(
            "Institution total:",
            ranking.length
        );


        console.log(
            "Homepage TOP 3:",
            top3
        );


        top3.forEach(
            function (item, index) {

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


                if (score) {

                    score.textContent =
                        item.gpa5
                            .toLocaleString(
                                "en-US"
                            );

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
    catch (error) {

        console.error(
            "Homepage institution error:",
            error
        );

    }

}


/* =========================================================
   HOMEPAGE QUICK STATS
========================================================= */

async function loadHomepageStats() {

    try {

        const data =
            await loadInstitutionResults();


        const institutions =
            createUniqueInstitutions(
                data
            );


        const districts =
            new Set();


        let totalStudents =
            0;


        institutions.forEach(
            function (item) {

                if (
                    item.district
                ) {

                    districts.add(
                        item.district
                            .trim()
                            .toUpperCase()
                    );

                }


                totalStudents +=
                    item.appeared;

            }
        );


        /*
         * Institution total
         */

        const institutionElement =
            document.getElementById(
                "statInstitutions"
            );


        if (
            institutionElement
        ) {

            institutionElement.textContent =
                institutions.length
                    .toLocaleString(
                        "en-US"
                    );

        }


        /*
         * District total
         */

        const districtElement =
            document.getElementById(
                "statDistricts"
            );


        if (
            districtElement
        ) {

            districtElement.textContent =
                districts.size
                    .toLocaleString(
                        "en-US"
                    );

        }


        /*
         * Student total
         */

        const studentElement =
            document.getElementById(
                "statStudents"
            );


        if (
            studentElement
        ) {

            studentElement.textContent =
                totalStudents
                    .toLocaleString(
                        "en-US"
                    );

        }


        console.log(
            "Homepage statistics:",
            {
                institutions:
                    institutions.length,

                districts:
                    districts.size,

                students:
                    totalStudents
            }
        );

    }
    catch (error) {

        console.error(
            "Homepage statistics error:",
            error
        );

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
        return;
    }


    /*
     * Keep your existing Supabase
     * visit system unchanged.
     */

}


/* =========================================================
   START
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        await Promise.all([

            loadHomepageTop3(),

            loadHomepageStats(),

            loadTotalVisits()

        ]);


        console.log(
            "✓ CTGBoardRanking homepage loaded"
        );

    }
);