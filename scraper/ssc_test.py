name: SSC Test

on:
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: ssc-ranking-update
  cancel-in-progress: false

jobs:
  test:
    runs-on: ubuntu-latest

    steps:

      # =====================================================
      # CHECKOUT
      # =====================================================

      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: main

      # =====================================================
      # PYTHON
      # =====================================================

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4

      # =====================================================
      # SHOW EXISTING DATA
      # =====================================================

      - name: Show existing collection
        run: |
          echo "========================================"
          echo "EXISTING SSC DATA"
          echo "========================================"

          if [ -f scraper/students.json ]; then
            python - <<'PY'
          import json

          path = "scraper/students.json"

          with open(path, "r", encoding="utf-8") as f:
              data = json.load(f)

          if isinstance(data, list):
              print("Existing students:", len(data))

              if data:
                  print("First roll:", data[0].get("roll"))
                  print("Last roll:", data[-1].get("roll"))
          else:
              print("ERROR: students.json is not a list")
          PY
          else
            echo "students.json not found"
          fi

      # =====================================================
      # RUN SSC COLLECTION
      # =====================================================

      - name: Run SSC data collection
        run: |
          python scraper/ssc_test.py

      # =====================================================
      # GENERATE INSTITUTION STATISTICS
      # =====================================================

      - name: Generate institution statistics
        run: |
          python scraper/institution_stats.py

      # =====================================================
      # CONVERT INSTITUTION CSV
      # =====================================================

      - name: Convert institution CSV
        run: |
          python scraper/csv_to_institutions.py

      # =====================================================
      # VALIDATE INSTITUTION DATA
      # =====================================================

      - name: Validate institution data
        run: |
          python scraper/ranking_validator.py

      # =====================================================
      # INSTITUTION RANKING
      # =====================================================

      - name: Calculate institution ranking
        run: |
          python scraper/ranking_engine.py

      # =====================================================
      # DISTRICT RANKING
      # =====================================================

      - name: Calculate district ranking
        run: |
          python scraper/district_ranking.py

      # =====================================================
      # STUDENT RANKING
      # =====================================================

      - name: Calculate student ranking
        run: |
          python scraper/student_ranking.py

      # =====================================================
      # YEAR RANKING
      # =====================================================

      - name: Calculate year-wise ranking
        run: |
          python scraper/year_ranking.py

      # =====================================================
      # BOARD RANKING
      # =====================================================

      - name: Calculate board ranking
        run: |
          python scraper/board_ranking.py

      # =====================================================
      # COLLECTION SUMMARY
      # =====================================================

      - name: Show collection summary
        if: always()
        run: |
          echo "========================================"
          echo "SSC COLLECTION SUMMARY"
          echo "========================================"

          if [ -f scraper/student_collection_summary.json ]; then
            cat scraper/student_collection_summary.json
          else
            echo "student_collection_summary.json not found"
          fi

          echo ""
          echo "========================================"
          echo "STUDENT COUNT"
          echo "========================================"

          if [ -f scraper/students.json ]; then
            python - <<'PY'
          import json

          path = "scraper/students.json"

          with open(path, "r", encoding="utf-8") as f:
              data = json.load(f)

          print("Total students:", len(data))

          if data:
              print("First roll:", data[0].get("roll"))
              print("Last roll:", data[-1].get("roll"))

          groups = {}

          for s in data:
              g = s.get("group", "Unknown")
              groups[g] = groups.get(g, 0) + 1

          print("")
          print("GROUP COUNTS")

          for group, count in groups.items():
              print(f"{group}: {count}")
          PY
          else
            echo "students.json not found"
          fi

      # =====================================================
      # CHECK JSON FILES
      # =====================================================

      - name: Validate JSON files
        run: |
          python - <<'PY'
          import json
          import os

          files = []

          for root, dirs, names in os.walk("scraper"):
              for name in names:
                  if name.endswith(".json"):
                      files.append(
                          os.path.join(root, name)
                      )

          failed = False

          for path in files:

              try:
                  with open(
                      path,
                      "r",
                      encoding="utf-8"
                  ) as f:
                      json.load(f)

                  size = os.path.getsize(path)

                  print(
                      f"OK: {path} "
                      f"({size / 1024 / 1024:.2f} MB)"
                  )

              except Exception as e:

                  print(
                      f"ERROR: {path} -> {e}"
                  )

                  failed = True

          if failed:
              raise SystemExit(
                  "JSON validation failed."
              )

          print("")
          print("All JSON files are valid.")
          PY

      # =====================================================
      # COMMIT EVERYTHING
      # =====================================================

      - name: Commit updated SSC data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          echo "========================================"
          echo "GIT STATUS BEFORE COMMIT"
          echo "========================================"

          git status --short

          # IMPORTANT:
          # Do NOT exclude students.json.
          # Do NOT restore students.json.
          # Do NOT remove student_ranking.json.

          git add scraper/

          echo ""
          echo "========================================"
          echo "STAGED FILES"
          echo "========================================"

          git status --short

          if git diff --cached --quiet; then
            echo ""
            echo "No changes to commit."
            exit 0
          fi

          echo ""
          echo "========================================"
          echo "COMMIT"
          echo "========================================"

          git commit -m "Update SSC ranking data"

      # =====================================================
      # SYNC WITH MAIN
      # =====================================================

      - name: Sync with latest main
        run: |
          echo "Fetching latest main..."

          git fetch origin main

          echo "Rebasing..."

          git rebase origin/main

      # =====================================================
      # PUSH
      # =====================================================

      - name: Push updated SSC data
        run: |
          echo "========================================"
          echo "PUSHING UPDATED DATA"
          echo "========================================"

          git push origin HEAD:main

          echo ""
          echo "========================================"
          echo "✓ SSC DATA PUSHED SUCCESSFULLY"
          echo "========================================"

      # =====================================================
      # FINAL CHECK
      # =====================================================

      - name: Final student count
        if: always()
        run: |
          echo "========================================"
          echo "FINAL STUDENT DATA"
          echo "========================================"

          if [ -f scraper/students.json ]; then

            python - <<'PY'
          import json

          with open(
              "scraper/students.json",
              "r",
              encoding="utf-8"
          ) as f:
              students = json.load(f)

          print(
              "Final total students:",
              len(students)
          )

          if students:
              print(
                  "First roll:",
                  students[0].get("roll")
              )

              print(
                  "Last roll:",
                  students[-1].get("roll")
              )
          PY

          else
            echo "students.json not found"
          fi

      # =====================================================
      # BACKUP
      # =====================================================

      - name: Upload SSC data backup
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: ssc-data
          path: scraper/
          if-no-files-found: warn
