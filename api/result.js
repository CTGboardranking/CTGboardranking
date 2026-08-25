export default async function handler(req, res) {
  // =====================================================
  // CORS
  // =====================================================

  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "GET") {
    return res.status(405).json({
      success: false,
      message: "Method not allowed"
    });
  }

  // =====================================================
  // ROLL
  // =====================================================

  const roll = String(req.query.roll || "").trim();

  if (!roll) {
    return res.status(400).json({
      success: false,
      message: "Roll number is required."
    });
  }

  if (!/^\d+$/.test(roll)) {
    return res.status(400).json({
      success: false,
      message: "Invalid roll number."
    });
  }

  // =====================================================
  // SUPABASE CONFIG
  // =====================================================

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_KEY;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.error("Missing Supabase environment variables");

    return res.status(500).json({
      success: false,
      message: "Server configuration error."
    });
  }

  const headers = {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json"
  };

  try {

    // ===================================================
    // 1. GET STUDENT
    // IMPORTANT:
    // total_score এখানে SELECT করা হয়নি
    // কারণ columnটি database-এ নেই।
    // ===================================================

    const studentUrl =
      `${SUPABASE_URL}/rest/v1/student_results` +
      `?select=id,year,exam,roll,registration,student_name,institution,institution_code,district,group_name,gpa,result_status` +
      `&roll=eq.${encodeURIComponent(roll)}` +
      `&limit=1`;

    const studentResponse = await fetch(
      studentUrl,
      {
        method: "GET",
        headers
      }
    );

    if (!studentResponse.ok) {
      const errorText =
        await studentResponse.text();

      console.error(
        "Student result Supabase error:",
        errorText
      );

      return res.status(500).json({
        success: false,
        message: "Unable to load result."
      });
    }

    const studentData =
      await studentResponse.json();

    if (
      !studentData ||
      studentData.length === 0
    ) {
      return res.status(404).json({
        success: false,
        message: `No result found for roll ${roll}.`
      });
    }

    const student =
      studentData[0];


    // ===================================================
    // 2. GET SUBJECT RESULTS
    // ===================================================

    let subjects = [];

    const subjectUrl =
      `${SUPABASE_URL}/rest/v1/student_subject_results` +
      `?select=*` +
      `&student_result_id=eq.${encodeURIComponent(student.id)}` +
      `&order=id.asc`;

    const subjectResponse = await fetch(
      subjectUrl,
      {
        method: "GET",
        headers
      }
    );

    if (subjectResponse.ok) {

      const subjectData =
        await subjectResponse.json();

      if (Array.isArray(subjectData)) {
        subjects = subjectData;
      }

    } else {

      const subjectError =
        await subjectResponse.text();

      console.warn(
        "Subject result error:",
        subjectError
      );

    }


    // ===================================================
    // 3. CALCULATE TOTAL SCORE
    // ===================================================

    let totalScore = 0;

    let validMarks = 0;

    subjects.forEach((subject) => {

      const rawMark =
        subject.marks ??
        subject.mark ??
        subject.total_marks ??
        subject.total_mark ??
        null;

      const mark =
        Number(rawMark);

      if (
        Number.isFinite(mark)
      ) {

        totalScore += mark;

        validMarks++;

      }

    });


    if (validMarks === 0) {
      totalScore = null;
    }


    // ===================================================
    // 4. STUDENT RANK
    //
    // Rank is calculated from all students' subject marks.
    //
    // IMPORTANT:
    // student_results.total_score ব্যবহার করা হয়নি।
    // ===================================================

    let studentRank = null;

    try {

      // Get all student IDs
      const allStudentsUrl =
        `${SUPABASE_URL}/rest/v1/student_results` +
        `?select=id,roll` +
        `&order=id.asc`;

      const allStudentsResponse =
        await fetch(
          allStudentsUrl,
          {
            method: "GET",
            headers
          }
        );


      if (allStudentsResponse.ok) {

        const allStudents =
          await allStudentsResponse.json();


        if (
          Array.isArray(allStudents) &&
          allStudents.length > 0
        ) {

          /*
           * Get subject marks for all students.
           *
           * We request only the columns needed.
           */

          const allSubjectsUrl =
            `${SUPABASE_URL}/rest/v1/student_subject_results` +
            `?select=student_result_id,marks,mark,total_marks,total_mark`;

          const allSubjectsResponse =
            await fetch(
              allSubjectsUrl,
              {
                method: "GET",
                headers
              }
            );


          if (allSubjectsResponse.ok) {

            const allSubjects =
              await allSubjectsResponse.json();


            if (
              Array.isArray(allSubjects)
            ) {

              const totals =
                new Map();


              // -----------------------------------------
              // Calculate total for every student
              // -----------------------------------------

              allSubjects.forEach(
                (subject) => {

                  const studentId =
                    String(
                      subject.student_result_id
                    );


                  const rawMark =
                    subject.marks ??
                    subject.mark ??
                    subject.total_marks ??
                    subject.total_mark ??
                    null;


                  const mark =
                    Number(rawMark);


                  if (
                    !Number.isFinite(mark)
                  ) {
                    return;
                  }


                  totals.set(
                    studentId,
                    (
                      totals.get(studentId) ||
                      0
                    ) + mark
                  );

                }
              );


              // -----------------------------------------
              // Create ranking
              // -----------------------------------------

              const ranking =
                allStudents

                  .map(
                    (item) => {

                      const id =
                        String(item.id);

                      const total =
                        totals.get(id);

                      return {

                        id,

                        roll:
                          item.roll,

                        total:
                          Number.isFinite(total)
                            ? total
                            : null

                      };

                    }
                  )

                  .filter(
                    (item) =>
                      item.total !== null
                  )

                  .sort(
                    (a, b) =>
                      b.total - a.total
                  );


              // -----------------------------------------
              // Find current student's rank
              // -----------------------------------------

              const currentIndex =
                ranking.findIndex(
                  (item) =>
                    item.id ===
                    String(student.id)
                );


              if (
                currentIndex !== -1
              ) {

                /*
                 * Competition ranking:
                 *
                 * 1000
                 * 1000
                 * 999
                 *
                 * Rank:
                 * 1
                 * 1
                 * 3
                 */

                const currentTotal =
                  ranking[currentIndex].total;


                studentRank =
                  ranking.filter(
                    (item) =>
                      item.total >
                      currentTotal
                  ).length + 1;

              }

            }

          } else {

            const rankError =
              await allSubjectsResponse.text();

            console.warn(
              "Ranking subject query error:",
              rankError
            );

          }

        }

      }

    }

    catch (rankError) {

      /*
       * Ranking fail হলেও result বন্ধ হবে না।
       */

      console.warn(
        "Rank calculation failed:",
        rankError
      );

      studentRank = null;

    }


    // ===================================================
    // 5. NORMALIZE SUBJECTS
    // ===================================================

    const normalizedSubjects =
      subjects.map(
        (subject) => {

          const subjectName =
            subject.subject_name ??
            subject.subject ??
            subject.subject_title ??
            subject.subject_code ??
            subject.code ??
            "—";


          const marks =
            subject.marks ??
            subject.mark ??
            subject.total_marks ??
            subject.total_mark ??
            null;


          const grade =
            subject.grade ??
            subject.grade_name ??
            "—";


          return {

            id:
              subject.id ?? null,

            subject_name:
              subjectName,

            subject:
              subject.subject ??
              subjectName,

            subject_code:
              subject.subject_code ??
              subject.code ??
              null,

            code:
              subject.code ??
              subject.subject_code ??
              null,

            marks:
              marks,

            mark:
              marks,

            grade:
              grade

          };

        }
      );


    // ===================================================
    // 6. FINAL RESPONSE
    // ===================================================

    return res.status(200).json({

      success: true,

      student: {

        id:
          student.id,

        year:
          student.year,

        exam:
          student.exam,

        roll:
          student.roll,

        registration:
          student.registration,

        student_name:
          student.student_name,

        institution:
          student.institution,

        institution_code:
          student.institution_code,

        district:
          student.district,

        group_name:
          student.group_name,

        gpa:
          student.gpa,

        result_status:
          student.result_status,

        /*
         * Calculated values
         */

        total_score:
          totalScore,

        student_rank:
          studentRank,

        subjects:
          normalizedSubjects

      }

    });

  }

  catch (error) {

    console.error(
      "Result API error:",
      error
    );

    return res.status(500).json({

      success: false,

      message:
        "Internal server error."

    });

  }

}