/* =========================================================
   CTGBoardRanking — MAIN SCRIPT
   Complete replacement
========================================================= */

"use strict";

/* =========================================================
   DARK MODE
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

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

    initializeRanking();

});


/* =========================================================
   JSON LOADER
========================================================= */

async function loadJSON(paths) {

    for (const path of paths) {

        try {

            const response =
                await fetch(
                    path + "?v=" + Date.now(),
                    {
                        cache: "no-store"
                    }
                );

            if (!response.ok) {
                console.warn(
                    "Failed:",
                    path,
                    response.status
                );
                continue;
            }

            const json =
                await response.json();

            console.log(
                "✓ JSON loaded:",
                path
            );

            return json;

        } catch (error) {

            console.warn(
                "Cannot load:",
                path,
                error
            );

        }

    }

    throw new Error(
        "JSON file could not be loaded"
    );
}


/* =========================================================
   GET ARRAY FROM JSON
========================================================= */

function getArray(json) {

    if (Array.isArray(json)) {
        return json;
    }

    if (
        json &&
        Array.isArray(json.institutions)
    ) {
        return json.institutions;
    }

    if (
        json &&
        Array.isArray(json.results)
    ) {
        return json.results;
    }

    if (
        json &&
        Array.isArray(json.data)
    ) {
        return json.data;
    }

    if (
        json &&
        Array.isArray(json.ranking)
    ) {
        return json.ranking;
    }

    return [];
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
   NORMALIZE INSTITUTION
========================================================= */

function normalizeInstitution(item) {

    const institution =
        String(
            item.institution_name ??
            item.institution ??
            item.institute ??
            item.name ??
            item.school_name ??
            item.college_name ??
            ""
        ).trim();


    const eiin =
        String(
            item.eiin ??
            item.EIIN ??
            item.eiin_no ??
            ""
        ).trim();


    const district =
        String(
            item.district ??
            item.district_name ??
            item.District ??
            ""
        ).trim();


    const appeared =
        num(
            item.appeared ??
            item.total_students ??
            item.total_appeared ??
            item.students ??
            item.student_total
        );


    const passed =
        num(
            item.passed ??
            item.total_passed ??
            item.pass
        );


    let passRate =
        num(
            item.passing_rate ??
            item.pass_rate ??
            item.passingRate ??
            item.pass_percentage
        );


    const gpa5 =
        num(
            item.gpa5 ??
            item.gpa_5 ??
            item.gpa5_count ??
            item.gpa_5_count ??
            item.total_gpa5 ??
            item.gpa5_students
        );


    if (
        passRate === 0 &&
        appeared > 0 &&
        passed >= 0
    ) {

        passRate =
            (passed / appeared) * 100;

    }


    return {

        eiin,

        institution,

        district,

        appeared,

        passed,

        passRate,

        gpa5

    };

}


/* =========================================================
   UNIQUE INSTITUTIONS
========================================================= */

function getUniqueInstitutions(data) {

    const map =
        new Map();


    data.forEach(raw => {

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

        } else {

            const old =
                map.get(key);


            /*
             * Keep the record with
             * the larger student count.
             */

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
   LOAD INSTITUTION DATA
========================================================= */

async function getInstitutionData() {

    const json =
        await loadJSON([

            "institution_results.json",

            "scraper/institution_results.json"

        ]);


    const data =
        getArray(json);


    if (!data.length) {

        throw new Error(
            "institution_results.json contains no records"
        );

    }


    console.log(
        "Institution records:",
        data.length
    );


    return data;

}


/* =========================================================
   TOP 3 INSTITUTIONS
========================================================= */

async function loadTopInstitutions(data) {

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


    const institutions =
        getUniqueInstitutions(data);


    /*
     * Ranking:
     *
     * 1. GPA-5
     * 2. Pass Rate
     * 3. Passed
     * 4. Students
     */

    institutions.sort(
        (a, b) => {

            if (
                b.gpa5 !== a.gpa5
            ) {
                return b.gpa5 - a.gpa5;
            }

            if (
                b.passRate !== a.passRate
            ) {
                return b.passRate - a.passRate;
            }

            if (
                b.passed !== a.passed
            ) {
                return b.passed - a.passed;
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
        "TOP 3:",
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
                    item.institution;

            }


            if (district) {

                district.textContent =
                    item.district ||
                    "Chattogram Board";

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


    /*
     * If fewer than 3 institutions,
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

async function loadQuickStats(data) {

    const institutions =
        getUniqueInstitutions(data);


    const districts =
        new Set();


    let students = 0;


    institutions.forEach(
        item => {

            if (item.district) {

                districts.add(
                    item.district
                        .toLowerCase()
                        .trim()
                );

            }


            students +=
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


    if (institutionElement) {

        institutionElement.textContent =
            institutions.length.toLocaleString(
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


    if (districtElement) {

        districtElement.textContent =
            districts.size.toLocaleString(
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


    if (studentElement) {

        studentElement.textContent =
            students.toLocaleString(
                "en-US"
            );

    }


    console.log(
        "Institution total:",
        institutions.length
    );


    console.log(
        "District total:",
        districts.size
    );


    console.log(
        "Student total:",
        students
    );

}


/* =========================================================
   STUDENT GROUP CARDS
========================================================= */

async function loadStudentCards() {

    try {

        const json =
            await loadJSON([

                "student_results.json",

                "scraper/student_results.json",

                "student_ranking.json",

                "scraper/student_ranking.json"

            ]);


        const students =
            getArray(json);


        if (!students.length) {
            return;
        }


        /*
         * Try to display top student
         * information in the 3 cards.
         */

        const cards =
            document.querySelectorAll(
                "#student-ranking .group-card"
            );


        if (!cards.length) {
            return;
        }


        const groups = [
            "science",
            "business",
            "humanities"
        ];


        groups.forEach(
            (group, index) => {

                const card =
                    cards[index];


                if (!card) {
                    return;
                }


                const filtered =
                    students.filter(
                        student => {

                            const value =
                                String(
                                    student.group ??
                                    student.group_name ??
                                    student.stream ??
                                    ""
                                )
                                .toLowerCase()
                                .trim();


                            if (
                                group === "science"
                            ) {
                                return (
                                    value.includes(
                                        "science"
                                    )
                                );
                            }


                            if (
                                group === "business"
                            ) {
                                return (
                                    value.includes(
                                        "business"
                                    ) ||
                                    value.includes(
                                        "commerce"
                                    )
                                );
                            }


                            if (
                                group === "humanities"
                            ) {
                                return (
                                    value.includes(
                                        "humanities"
                                    ) ||
                                    value.includes(
                                        "arts"
                                    )
                                );
                            }


                            return false;

                        }
                    );


                if (!filtered.length) {
                    return;
                }


                const student =
                    filtered[0];


                const name =
                    student.name ??
                    student.student_name ??
                    student.candidate_name;


                const gpa =
                    student.gpa ??
                    student.GPA ??
                    student.grade_point;


                const description =
                    card.querySelector("p");


                if (
                    name &&
                    description
                ) {

                    description.textContent =
                        String(name) +
                        (
                            gpa !== undefined
                                ? " · GPA " +
                                  String(gpa)
                                : ""
                        );

                }

            }
        );

    } catch (error) {

        console.warn(
            "Student data not loaded:",
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
     * Keep current value if
     * Supabase key has not been added.
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


    try {

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
                "Supabase HTTP " +
                response.status
            );

        }


        const data =
            await response.json();


        if (
            Array.isArray(data) &&
            data.length
        ) {

            element.textContent =
                Number(
                    data[0].total_visits || 0
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

    console.log(
        "CTGBoardRanking starting..."
    );


    try {

        const institutionData =
            await getInstitutionData();


        /*
         * Run institution functions
         */

        await Promise.all([

            loadTopInstitutions(
                institutionData
            ),

            loadQuickStats(
                institutionData
            ),

            loadStudentCards(),

            loadTotalVisits()

        ]);


        console.log(
            "✓ CTGBoardRanking loaded"
        );

    } catch (error) {

        console.error(
            "MAIN DATA ERROR:",
            error
        );


        /*
         * Show clear error instead
         * of infinite Loading...
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


            const info =
                row.querySelector(
                    ".rank-info span"
                );


            if (name) {
                name.textContent =
                    "Data unavailable";
            }


            if (info) {
                info.textContent =
                    "Check institution_results.json";
            }

        });

    }

}
