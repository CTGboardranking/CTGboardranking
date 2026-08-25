document.addEventListener("DOMContentLoaded", () => {

  const form = document.getElementById("resultForm");
  const rollInput = document.getElementById("rollInput");
  const clearBtn = document.getElementById("clearBtn");

  const searchBtn = document.getElementById("searchBtn");
  const searchBtnText = document.getElementById("searchBtnText");
  const searchSpinner = document.getElementById("searchSpinner");

  const errorMessage = document.getElementById("errorMessage");

  const resultSection = document.getElementById("resultSection");
  const emptyState = document.getElementById("emptyState");

  const newSearchBtn = document.getElementById("newSearchBtn");
  const downloadPdfBtn = document.getElementById("downloadPdfBtn");

  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");

  let currentStudent = null;


  /* =====================================================
     THEME
  ===================================================== */

  const savedTheme =
    localStorage.getItem("ctg-theme");

  if (savedTheme === "dark") {
    document.documentElement.classList.add("dark");

    if (themeIcon) {
      themeIcon.textContent = "☀";
    }
  }

  if (themeToggle) {

    themeToggle.addEventListener("click", () => {

      const isDark =
        document.documentElement.classList.toggle("dark");

      localStorage.setItem(
        "ctg-theme",
        isDark ? "dark" : "light"
      );

      if (themeIcon) {
        themeIcon.textContent =
          isDark ? "☀" : "☾";
      }

    });

  }


  /* =====================================================
     INPUT
  ===================================================== */

  if (rollInput) {

    rollInput.addEventListener("input", () => {

      rollInput.value =
        rollInput.value.replace(/\D/g, "");

      if (clearBtn) {

        clearBtn.classList.toggle(
          "hidden",
          !rollInput.value
        );

      }

      hideError();

    });

  }


  if (clearBtn) {

    clearBtn.addEventListener("click", () => {

      rollInput.value = "";

      clearBtn.classList.add("hidden");

      rollInput.focus();

    });

  }


  /* =====================================================
     SEARCH
  ===================================================== */

  if (form) {

    form.addEventListener(
      "submit",
      async (event) => {

        event.preventDefault();

        const roll =
          rollInput.value.trim();

        if (!roll) {

          showError(
            "Please enter a roll number."
          );

          rollInput.focus();

          return;
        }

        if (!/^\d+$/.test(roll)) {

          showError(
            "Please enter a valid numeric roll number."
          );

          return;
        }

        await searchResult(roll);

      }
    );

  }


  async function searchResult(roll) {

    setLoading(true);

    hideError();

    if (resultSection) {
      resultSection.classList.add("hidden");
    }

    try {

      const response =
        await fetch(
          `/api/result?roll=${encodeURIComponent(roll)}`,
          {
            method: "GET",
            headers: {
              "Accept": "application/json"
            },
            cache: "no-store"
          }
        );


      let data = null;

      try {
        data = await response.json();
      }

      catch {
        data = null;
      }


      if (
        !response.ok ||
        !data?.success
      ) {

        throw new Error(
          data?.message ||
          "Result not found."
        );

      }


      if (!data.student) {

        throw new Error(
          "Student result data is missing."
        );

      }


      currentStudent =
        data.student;


      renderResult(
        currentStudent
      );


      if (emptyState) {
        emptyState.classList.add("hidden");
      }


      if (resultSection) {

        resultSection.classList.remove(
          "hidden"
        );

        setTimeout(() => {

          resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
          });

        }, 100);

      }


    }

    catch (error) {

      console.error(
        "Result error:",
        error
      );

      showError(
        error.message ||
        "Unable to load result. Please try again."
      );


      if (emptyState) {
        emptyState.classList.remove(
          "hidden"
        );
      }

    }

    finally {

      setLoading(false);

    }

  }


  /* =====================================================
     RENDER RESULT
  ===================================================== */

  function renderResult(student) {

    setText(
      "studentName",
      student.name ||
      student.student_name
    );


    setText(
      "studentRoll",
      student.roll
    );


    setText(
      "studentReg",
      student.reg_no ||
      student.registration ||
      student.registration_no
    );


    setText(
      "studentGroup",
      student.group_name ||
      student.group
    );


    setText(
      "resultBoard",
      student.board ||
      "Chattogram Board"
    );


    setText(
      "resultStatus",
      student.result ||
      student.result_status ||
      "PASSED"
    );


    /* =================================================
       TOTAL SCORE
    ================================================= */

    setText(
      "totalScore",
      formatNumber(
        student.total_score
      )
    );


    /* =================================================
       GPA
    ================================================= */

    setText(
      "gpa",
      formatGPA(
        student.gpa
      )
    );


    /* =================================================
       INSTITUTION
    ================================================= */

    setText(
      "studentInstitute",
      student.institute ||
      student.institution
    );


    /* =================================================
       DISTRICT
    ================================================= */

    setText(
      "studentDistrict",
      student.district
    );


    /* =================================================
       FATHER / MOTHER
    ================================================= */

    setText(
      "fatherName",
      student.father_name
    );


    setText(
      "motherName",
      student.mother_name
    );


    /* =================================================
       STUDENT RANK
    ================================================= */

    const rank =
      student.student_rank ??
      student.studentRank ??
      student.rank ??
      student.overall_rank ??
      student.position ??
      student.merit_position ??
      null;


    setText(
      "studentRank",
      formatRank(rank)
    );


    /* =================================================
       SUBJECTS
    ================================================= */

    renderSubjects(
      student.subjects
    );

  }


  /* =====================================================
     SUBJECTS
  ===================================================== */

  function renderSubjects(subjects) {

    const body =
      document.getElementById(
        "subjectsBody"
      );


    if (!body) {
      return;
    }


    body.innerHTML = "";


    if (
      !Array.isArray(subjects) ||
      subjects.length === 0
    ) {

      body.innerHTML = `
        <tr>
          <td colspan="5"
              style="
                text-align:center;
                color:var(--muted);
                padding:25px;
              ">
            Subject information unavailable
          </td>
        </tr>
      `;


      const count =
        document.getElementById(
          "subjectCount"
        );

      if (count) {
        count.textContent =
          "0 Subjects";
      }

      return;
    }


    subjects.forEach(
      (subject, index) => {

        const row =
          document.createElement("tr");


        const subjectName =
          subject.subject ||
          subject.subject_name ||
          subject.name ||
          "Unknown Subject";


        const code =
          subject.code ||
          subject.subject_code ||
          "—";


        const mark =
          subject.mark ??
          subject.marks ??
          subject.total_marks ??
          "—";


        const grade =
          subject.grade ||
          subject.grade_name ||
          "—";


        row.innerHTML = `

          <td>
            ${index + 1}
          </td>

          <td class="subject-name">
            ${escapeHTML(subjectName)}
          </td>

          <td class="subject-code">
            ${escapeHTML(code)}
          </td>

          <td class="mark-cell">
            ${escapeHTML(String(mark))}
          </td>

          <td class="grade-cell ${gradeClass(grade)}">
            ${escapeHTML(grade)}
          </td>

        `;


        body.appendChild(row);

      }
    );


    const count =
      document.getElementById(
        "subjectCount"
      );


    if (count) {

      count.textContent =
        `${subjects.length} Subject${
          subjects.length !== 1
            ? "s"
            : ""
        }`;

    }

  }


  /* =====================================================
     GRADE CLASS
  ===================================================== */

  function gradeClass(grade) {

    const normalized =
      String(grade)
        .trim()
        .toUpperCase();


    if (normalized === "A+") {
      return "grade-a-plus";
    }

    if (normalized === "A") {
      return "grade-a";
    }

    if (normalized === "A-") {
      return "grade-a-minus";
    }

    if (normalized === "B") {
      return "grade-b";
    }

    if (normalized === "C") {
      return "grade-c";
    }

    if (normalized === "D") {
      return "grade-d";
    }

    if (normalized === "F") {
      return "grade-f";
    }

    return "";

  }


  /* =====================================================
     NEW SEARCH
  ===================================================== */

  if (newSearchBtn) {

    newSearchBtn.addEventListener(
      "click",
      () => {

        if (resultSection) {
          resultSection.classList.add(
            "hidden"
          );
        }

        if (emptyState) {
          emptyState.classList.remove(
            "hidden"
          );
        }

        rollInput.focus();

        window.scrollTo({
          top: 0,
          behavior: "smooth"
        });

      }
    );

  }


  /* =====================================================
     DOWNLOAD PDF
  ===================================================== */

  if (downloadPdfBtn) {

    downloadPdfBtn.addEventListener(
      "click",
      downloadPDF
    );

  }


  async function downloadPDF() {

    if (!currentStudent) {

      showError(
        "Please search for a result first."
      );

      return;

    }


    /* ================================================
       CHECK PDF LIBRARIES
    ================================================ */

    if (
      !window.jspdf ||
      !window.html2canvas
    ) {

      showError(
        "PDF library is still loading. Please wait a moment and try again."
      );

      return;

    }


    const originalHTML =
      downloadPdfBtn.innerHTML;


    downloadPdfBtn.disabled =
      true;


    downloadPdfBtn.innerHTML =
      `<span class="spinner"></span> Generating...`;


    const wasDark =
      document.documentElement
        .classList
        .contains("dark");


    try {

      /* ==============================================
         RESULT CARD
      ============================================== */

      const card =
        document.getElementById(
          "resultCard"
        );


      if (!card) {

        throw new Error(
          "Result card not found."
        );

      }


      /* ==============================================
         FORCE LIGHT MODE
      ============================================== */

      if (wasDark) {

        document.documentElement
          .classList
          .remove("dark");

      }


      /*
       * Give browser time to repaint.
       */

      await wait(250);


      /* ==============================================
         CAPTURE RESULT
      ============================================== */

      const canvas =
        await html2canvas(
          card,
          {
            scale: 2,
            useCORS: true,
            allowTaint: false,
            backgroundColor: "#ffffff",
            logging: false,
            imageTimeout: 15000,
            removeContainer: true,

            onclone: function(clonedDocument) {

              /*
               * Make sure cloned result is visible.
               */

              const clonedCard =
                clonedDocument.getElementById(
                  "resultCard"
                );

              if (clonedCard) {

                clonedCard.style.display =
                  "block";

                clonedCard.style.visibility =
                  "visible";

                clonedCard.style.opacity =
                  "1";

                clonedCard.style.background =
                  "#ffffff";

                clonedCard.style.color =
                  "#111113";

              }


              /*
               * Hide interactive elements
               * inside the PDF.
               */

              const buttons =
                clonedDocument.querySelectorAll(
                  ".result-actions"
                );

              buttons.forEach(
                element => {
                  element.style.display =
                    "none";
                }
              );

            }

          }
        );


      /* ==============================================
         RESTORE DARK MODE
      ============================================== */

      if (wasDark) {

        document.documentElement
          .classList
          .add("dark");

      }


      /* ==============================================
         CREATE PDF
      ============================================== */

      const {
        jsPDF
      } = window.jspdf;


      const pdf =
        new jsPDF({
          orientation: "portrait",
          unit: "mm",
          format: "a4",
          compress: true
        });


      const pageWidth =
        pdf.internal.pageSize.getWidth();


      const pageHeight =
        pdf.internal.pageSize.getHeight();


      const margin =
        12;


      const headerHeight =
        23;


      const footerHeight =
        13;


      const usableWidth =
        pageWidth -
        margin * 2;


      const usableHeight =
        pageHeight -
        margin -
        headerHeight -
        footerHeight;


      /* ==============================================
         IMAGE DIMENSIONS
      ============================================== */

      const imageHeight =
        (
          canvas.height *
          usableWidth
        ) /
        canvas.width;


      const imageData =
        canvas.toDataURL(
          "image/jpeg",
          0.95
        );


      /* ==============================================
         DATE
      ============================================== */

      const generatedDate =
        new Date()
          .toLocaleDateString(
            "en-GB",
            {
              day: "2-digit",
              month: "short",
              year: "numeric"
            }
          );


      /* ==============================================
         HEADER FUNCTION
      ============================================== */

      function drawPDFHeader() {

        /* Top line */

        pdf.setDrawColor(
          225,
          225,
          230
        );

        pdf.setLineWidth(
          0.35
        );

        pdf.line(
          margin,
          10,
          pageWidth - margin,
          10
        );


        /* CTGboardranking */

        pdf.setFont(
          "helvetica",
          "bold"
        );

        pdf.setFontSize(
          14
        );

        pdf.setTextColor(
          17,
          17,
          19
        );

        pdf.text(
          "CTGboardranking",
          margin,
          18
        );


        /* Generated by */

        pdf.setFont(
          "helvetica",
          "bold"
        );

        pdf.setFontSize(
          8
        );

        pdf.setTextColor(
          80,
          80,
          85
        );

        pdf.text(
          "Generated by Shadat",
          pageWidth - margin,
          16,
          {
            align: "right"
          }
        );


        /* Date */

        pdf.setFont(
          "helvetica",
          "normal"
        );

        pdf.setFontSize(
          7
        );

        pdf.setTextColor(
          110,
          110,
          115
        );

        pdf.text(
          generatedDate,
          pageWidth - margin,
          21,
          {
            align: "right"
          }
        );

      }


      /* ==============================================
         FOOTER FUNCTION
      ============================================== */

      function drawPDFFooter(pageNumber) {

        pdf.setDrawColor(
          225,
          225,
          230
        );

        pdf.setLineWidth(
          0.3
        );

        pdf.line(
          margin,
          pageHeight - 9,
          pageWidth - margin,
          pageHeight - 9
        );


        pdf.setFont(
          "helvetica",
          "bold"
        );

        pdf.setFontSize(
          7
        );

        pdf.setTextColor(
          215,
          0,
          21
        );

        pdf.text(
          "UNOFFICIAL NOTICE",
          margin,
          pageHeight - 4
        );


        pdf.setFont(
          "helvetica",
          "normal"
        );

        pdf.setFontSize(
          7
        );

        pdf.setTextColor(
          110,
          110,
          115
        );

        pdf.text(
          `Page ${pageNumber}`,
          pageWidth - margin,
          pageHeight - 4,
          {
            align: "right"
          }
        );

      }


      /* ==============================================
         ADD IMAGE TO MULTIPLE PAGES
      ============================================== */

      let remainingHeight =
        imageHeight;


      let sourceY =
        0;


      let pageNumber =
        1;


      /*
       * First page
       */

      drawPDFHeader();


      const firstPageHeight =
        Math.min(
          remainingHeight,
          usableHeight
        );


      const firstSourceHeight =
        (
          firstPageHeight *
          canvas.width
        ) /
        usableWidth;


      const firstCanvas =
        document.createElement(
          "canvas"
        );


      firstCanvas.width =
        canvas.width;


      firstCanvas.height =
        Math.max(
          1,
          Math.floor(
            firstSourceHeight
          )
        );


      const firstContext =
        firstCanvas.getContext(
          "2d"
        );


      firstContext.drawImage(
        canvas,
        0,
        Math.floor(sourceY),
        canvas.width,
        Math.floor(firstSourceHeight),
        0,
        0,
        firstCanvas.width,
        firstCanvas.height
      );


      const firstImage =
        firstCanvas.toDataURL(
          "image/jpeg",
          0.95
        );


      pdf.addImage(
        firstImage,
        "JPEG",
        margin,
        margin + headerHeight,
        usableWidth,
        firstPageHeight,
        undefined,
        "FAST"
      );


      remainingHeight -=
        firstPageHeight;


      sourceY +=
        firstSourceHeight;


      drawPDFFooter(
        pageNumber
      );


      /*
       * Remaining pages
       */

      while (
        remainingHeight > 0.5
      ) {

        pdf.addPage();

        pageNumber++;


        drawPDFHeader();


        const currentHeight =
          Math.min(
            remainingHeight,
            usableHeight
          );


        const sourceHeight =
          (
            currentHeight *
            canvas.width
          ) /
          usableWidth;


        const pageCanvas =
          document.createElement(
            "canvas"
          );


        pageCanvas.width =
          canvas.width;


        pageCanvas.height =
          Math.max(
            1,
            Math.floor(
              sourceHeight
            )
          );


        const pageContext =
          pageCanvas.getContext(
            "2d"
          );


        pageContext.drawImage(
          canvas,
          0,
          Math.floor(sourceY),
          canvas.width,
          Math.floor(sourceHeight),
          0,
          0,
          pageCanvas.width,
          pageCanvas.height
        );


        const pageImage =
          pageCanvas.toDataURL(
            "image/jpeg",
            0.95
          );


        pdf.addImage(
          pageImage,
          "JPEG",
          margin,
          margin + headerHeight,
          usableWidth,
          currentHeight,
          undefined,
          "FAST"
        );


        drawPDFFooter(
          pageNumber
        );


        remainingHeight -=
          currentHeight;


        sourceY +=
          sourceHeight;

      }


      /* ==============================================
         FILE NAME
      ============================================== */

      const roll =
        String(
          currentStudent.roll ||
          "student"
        );


      const studentName =
        currentStudent.name ||
        currentStudent.student_name ||
        "result";


      const safeName =
        String(studentName)
          .replace(
            /[^a-z0-9]+/gi,
            "-"
          )
          .replace(
            /^-+|-+$/g,
            ""
          )
          .toLowerCase();


      const filename =
        `CTGboardranking-SSC-2026-${roll}-${safeName || "result"}.pdf`;


      /* ==============================================
         DOWNLOAD
      ============================================== */

      pdf.save(
        filename
      );


    }

    catch (error) {

      console.error(
        "PDF generation error:",
        error
      );


      /*
       * Restore dark mode if needed.
       */

      if (wasDark) {

        document.documentElement
          .classList
          .add("dark");

      }


      showError(
        "Unable to generate PDF. Please try again."
      );

    }

    finally {

      downloadPdfBtn.disabled =
        false;

      downloadPdfBtn.innerHTML =
        originalHTML;

    }

  }


  /* =====================================================
     LOADING
  ===================================================== */

  function setLoading(loading) {

    if (!searchBtn) {
      return;
    }


    searchBtn.disabled =
      loading;


    if (
      searchBtnText &&
      searchSpinner
    ) {

      if (loading) {

        searchBtnText.classList.add(
          "hidden"
        );

        searchSpinner.classList.remove(
          "hidden"
        );

      }

      else {

        searchBtnText.classList.remove(
          "hidden"
        );

        searchSpinner.classList.add(
          "hidden"
        );

      }

    }

  }


  /* =====================================================
     ERROR
  ===================================================== */

  function showError(message) {

    if (!errorMessage) {
      return;
    }


    errorMessage.textContent =
      message;


    errorMessage.classList.remove(
      "hidden"
    );

  }


  function hideError() {

    if (!errorMessage) {
      return;
    }


    errorMessage.classList.add(
      "hidden"
    );


    errorMessage.textContent =
      "";

  }


  /* =====================================================
     HELPERS
  ===================================================== */

  function setText(id, value) {

    const element =
      document.getElementById(id);


    if (!element) {
      return;
    }


    element.textContent =
      safeText(value);

  }


  function safeText(value) {

    if (
      value === null ||
      value === undefined ||
      String(value).trim() === ""
    ) {

      return "—";

    }


    return String(value);

  }


  function formatNumber(value) {

    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {

      return "—";

    }


    const number =
      Number(value);


    if (Number.isNaN(number)) {

      return safeText(value);

    }


    return number.toLocaleString(
      "en-US"
    );

  }


  function formatGPA(value) {

    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {

      return "—";

    }


    const number =
      Number(value);


    if (Number.isNaN(number)) {

      return safeText(value);

    }


    return number.toFixed(2);

  }


  function formatRank(value) {

    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {

      return "—";

    }


    const number =
      Number(value);


    if (Number.isNaN(number)) {

      return safeText(value);

    }


    return `#${number.toLocaleString("en-US")}`;

  }


  function escapeHTML(value) {

    return String(value)
      .replace(
        /&/g,
        "&amp;"
      )
      .replace(
        /</g,
        "&lt;"
      )
      .replace(
        />/g,
        "&gt;"
      )
      .replace(
        /"/g,
        "&quot;"
      )
      .replace(
        /'/g,
        "&#039;"
      );

  }


  function wait(ms) {

    return new Promise(
      resolve =>
        setTimeout(
          resolve,
          ms
        )
    );

  }

});