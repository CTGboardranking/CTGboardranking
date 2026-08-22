import json
import os


INPUT_FILE = "scraper/validated_institutions.json"
OUTPUT_FILE = "scraper/institution_ranking.json"


# ============================================================
# CONFIGURATION
# ============================================================

GPA5_WEIGHT = 50
AVERAGE_GPA_WEIGHT = 30
GRADE_WEIGHT = 20


# ============================================================
# LOAD DATA
# ============================================================

if not os.path.exists(INPUT_FILE):
    raise SystemExit(
        f"Input file not found: {INPUT_FILE}"
    )


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:
    institutions = json.load(f)


if not isinstance(institutions, list):
    raise SystemExit(
        "institutions.json must contain a JSON list."
    )


# ============================================================
# NORMALIZE
# ============================================================

def clamp(value, minimum=0, maximum=100):
    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def calculate_grade_score(grade_distribution):
    """
    Grade performance score.

    A+ = 100
    A  = 85
    A- = 70
    B  = 55
    C  = 40
    D  = 25
    F  = 0
    """

    grade_points = {
        "A+": 100,
        "A": 85,
        "A-": 70,
        "B": 55,
        "C": 40,
        "D": 25,
        "F": 0
    }

    total = sum(
        grade_distribution.values()
    )

    if total == 0:
        return 0

    weighted_total = 0

    for grade, count in grade_distribution.items():

        point = grade_points.get(
            grade,
            0
        )

        weighted_total += (
            point * count
        )

    return weighted_total / total


# ============================================================
# CALCULATE SCORE
# ============================================================

ranking = []


for institution in institutions:

    name = str(
        institution.get(
            "institute",
            ""
        )
    ).strip()

    if not name:
        continue


    total_students = int(
        institution.get(
            "total_students",
            0
        ) or 0
    )


    gpa5_count = int(
        institution.get(
            "gpa_5_count",
            0
        ) or 0
    )


    average_gpa = float(
        institution.get(
            "average_gpa",
            0
        ) or 0
    )


    grade_distribution = institution.get(
        "grade_distribution",
        {}
    )


    # --------------------------------------------------------
    # GPA-5 RATE
    # --------------------------------------------------------

    if total_students > 0:

        gpa5_rate = (
            gpa5_count
            / total_students
        ) * 100

    else:

        gpa5_rate = 0


    gpa5_rate = clamp(
        gpa5_rate
    )


    # --------------------------------------------------------
    # GPA SCORE
    # --------------------------------------------------------

    average_gpa_score = (
        average_gpa / 5.0
    ) * 100

    average_gpa_score = clamp(
        average_gpa_score
    )


    # --------------------------------------------------------
    # GRADE SCORE
    # --------------------------------------------------------

    grade_score = calculate_grade_score(
        grade_distribution
    )

    grade_score = clamp(
        grade_score
    )


    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    final_score = (
        (gpa5_rate * GPA5_WEIGHT / 100)
        +
        (average_gpa_score * AVERAGE_GPA_WEIGHT / 100)
        +
        (grade_score * GRADE_WEIGHT / 100)
    )


    ranking.append({

        "institute": name,

        "total_students":
            total_students,

        "gpa_5_count":
            gpa5_count,

        "gpa_5_percentage":
            round(
                gpa5_rate,
                2
            ),

        "average_gpa":
            round(
                average_gpa,
                2
            ),

        "grade_score":
            round(
                grade_score,
                2
            ),

        "final_score":
            round(
                final_score,
                2
            )
    })


# ============================================================
# SORT
# ============================================================

ranking.sort(
    key=lambda x: (
        -x["final_score"],
        -x["gpa_5_count"],
        -x["total_students"],
        x["institute"].lower()
    )
)


# ============================================================
# ASSIGN RANK
# ============================================================

current_rank = 0
previous_score = None

for index, item in enumerate(
    ranking,
    start=1
):

    score = item[
        "final_score"
    ]

    if score != previous_score:

        current_rank = index

    item["rank"] = current_rank

    previous_score = score


# ============================================================
# SAVE
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        ranking,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# DISPLAY TOP 20
# ============================================================

print(
    "\n===== INSTITUTION RANKING =====\n"
)

for item in ranking[:20]:

    print(
        f"Rank #{item['rank']} | "
        f"{item['institute']} | "
        f"Score: {item['final_score']} | "
        f"GPA-5: {item['gpa_5_count']} | "
        f"Average GPA: {item['average_gpa']}"
    )


print(
    "\nTotal institutions:",
    len(ranking)
)

print(
    "Saved:",
    OUTPUT_FILE
)

print(
    "\n===== DONE ====="
)