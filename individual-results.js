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


  /* ================================
     THEME
  ================================= */

  const savedTheme = localStorage.getItem("ctg-theme");

  if (savedTheme === "dark") {
    document.documentElement.classList.add("dark");
    themeIcon.textContent = "☀";
  }

  themeToggle.addEventListener("click", () => {

    const isDark =
      document.documentElement.classList.toggle("dark");

    localStorage.setItem(
      "ctg-theme",
      isDark ? "dark" : "light"
    );

    themeIcon.textContent =
      isDark ? "☀" : "☾";
  });


  /* ================================
     INPUT
  ================================= */

  rollInput.addEventListener("input", () => {

    rollInput.value =
      rollInput.value.replace(/\D/g, "");

    clearBtn.classList.toggle(
      "hidden",
      !rollInput.value
    );

    hideError();
  });


  clearBtn.addEventListener("click", () => {

    rollInput.value = "";

    clearBtn.classList.add("hidden");

    rollInput.focus();
  });


  /* ================================
     SEARCH
  ================================= */

  form.addEventListener("submit", async (event) => {

    event.preventDefault();

    const roll = rollInput.value.trim();

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
  });


  async function searchResult(roll) {

    setLoading(true);

    hideError();

    resultSection.classList.add("hidden");

    try {

      const response = await fetch(
        `/api/result?roll=${encodeURIComponent(roll)}`,
        {
          method: "GET",
          headers: {
            "Accept": "application/json"
          }
        }
      );

      let data = null;

      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok || !data?.success) {

        throw new Error(
          data?.message ||
          "Result not found."
        );
      }

      currentStudent = data.student;

      renderResult(currentStudent);

      emptyState.classList.add("hidden");

      resultSection.classList.remove("hidden");

      setTimeout(() => {
        resultSection.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      }, 100);

    } catch (error) {

      console.error(error);

      showError(
        error.message ||
        "Unable to load result. Please try again."
      );

      emptyState.classList.remove("hidden");

    } finally {

      setLoading(false);
    }
  }


  /* ================================
     RENDER RESULT
  ================================= */

  function renderResult(student) {

    document.getElementById("studentName").textContent =
      safeText(student.name);

    document.getElementById("studentRoll").textContent =
      safeText(student.roll);

    document.getElementById("studentReg").textContent =
      safeText(student.reg_no);

    document.getElementById("studentGroup").textContent =
      safeText(
        student.group_name ||
        student.group ||
        "—"
      );

    document.getElementById("resultBoard").textContent =
      safeText(
        student.board ||
        "Chattogram Board"
      );

    document.getElementById("resultStatus").textContent =
      safeText(
        student.result ||
        "PASSED"
      );

    document.getElementById("totalScore").textContent =
      formatNumber(student.total_score);

    document.getElementById("gpa").textContent =
      formatGPA(student.gpa);

    document.getElementById("studentInstitute").textContent =
      safeText(student.institute);

    document.getElementById("studentDistrict").textContent =
      safeText(student.district);

    document.getElementById("fatherName").textContent =
      safeText(student.father_name);

    document.getElementById("motherName").textContent =
      safeText(student.mother_name);


    renderSubjects(student.subjects);
  }


  /* ================================
     SUBJECTS
  ================================= */

  function renderSubjects(subjects) {

    const body =
      document.getElementById("subjectsBody");

    body.innerHTML = "";

    if (!Array.isArray(subjects) || subjects.length === 0) {

      body.innerHTML = `
        <tr>
          <td colspan="5"
              style="text-align:center;color:var(--muted);">
            Subject information unavailable
          </td>
        </tr>
      `;

      document.getElementById(
        "subjectCount"
      ).textContent = "0 Subjects";

      return;
    }


    subjects.forEach((subject, index) => {

      const row =
        document.createElement("tr");

      const subjectName =
        subject.subject ||
        subject.name ||
        "Unknown Subject";

      const code =
        subject.code ||
        "—";

      const mark =
        subject.mark ??
        "—";

      const grade =
        subject.grade ||
        "—";

      row.innerHTML = `
        <td>${index + 1}</td>

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
    });


    document.getElementById(
      "subjectCount"
    ).textContent =
      `${subjects.length} Subject${subjects.length !== 1 ? "s" : ""}`;
  }


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


  /* ================================
     NEW SEARCH
  ================================= */

  newSearchBtn.addEventListener("click", () => {

    resultSection.classList.add("hidden");

    emptyState.classList.remove("hidden");

    rollInput.focus();

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  });


  /* ================================
     PDF
  ================================= */

  downloadPdfBtn.addEventListener(
    "click",
    downloadPDF
  );


  async function downloadPDF() {

    if (!currentStudent) {

      showError(
        "Please search for a result first."
      );

      return;
    }

    if (
      !window.jspdf ||
      !window.html2canvas
    ) {

      showError(
        "PDF library is still loading. Please try again."
      );

      return;
    }


    const originalText =
      downloadPdfBtn.innerHTML;

    downloadPdfBtn.disabled = true;

    downloadPdfBtn.innerHTML =
      `<span class="spinner"></span> Generating...`;


    try {

      const card =
        document.getElementById("resultCard");

      /*
       * Temporarily make sure the result is
       * rendered in light mode for a clean PDF.
       */
      const wasDark =
        document.documentElement.classList.contains("dark");

      if (wasDark) {
        document.documentElement.classList.remove("dark");
      }


      const canvas =
        await html2canvas(card, {
          scale: 2,
          useCORS: true,
          backgroundColor: "#ffffff",
          logging: false
        });


      if (wasDark) {
        document.documentElement.classList.add("dark");
      }


      const imageData =
        canvas.toDataURL(
          "image/png",
          1.0
        );


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

      const margin = 8;

      const usableWidth =
        pageWidth - margin * 2;

      const imageHeight =
        (canvas.height * usableWidth) /
        canvas.width;


      let heightLeft = imageHeight;
      let position = margin;


      pdf.addImage(
        imageData,
        "PNG",
        margin,
        position,
        usableWidth,
        imageHeight,
        undefined,
        "FAST"
      );


      heightLeft -=
        pageHeight - margin * 2;


      while (heightLeft > 0) {

        position =
          -(imageHeight - heightLeft) +
          margin;

        pdf.addPage();

        pdf.addImage(
          imageData,
          "PNG",
          margin,
          position,
          usableWidth,
          imageHeight,
          undefined,
          "FAST"
        );

        heightLeft -=
          pageHeight - margin * 2;
      }


      const roll =
        String(currentStudent.roll || "student");

      const safeName =
        String(currentStudent.name || "result")
          .replace(/[^a-z0-9]+/gi, "-")
          .replace(/^-+|-+$/g, "")
          .toLowerCase();


      pdf.save(
        `SSC-2026-${roll}-${safeName}.pdf`
      );

    } catch (error) {

      console.error(
        "PDF generation error:",
        error
      );

      showError(
        "Unable to generate PDF. Please try again."
      );

    } finally {

      downloadPdfBtn.disabled = false;

      downloadPdfBtn.innerHTML =
        originalText;
    }
  }


  /* ================================
     LOADING
  ================================= */

  function setLoading(loading) {

    searchBtn.disabled = loading;

    if (loading) {

      searchBtnText.classList.add("hidden");

      searchSpinner.classList.remove("hidden");

    } else {

      searchBtnText.classList.remove("hidden");

      searchSpinner.classList.add("hidden");
    }
  }


  /* ================================
     ERROR
  ================================= */

  function showError(message) {

    errorMessage.textContent = message;

    errorMessage.classList.remove("hidden");
  }


  function hideError() {

    errorMessage.classList.add("hidden");

    errorMessage.textContent = "";
  }


  /* ================================
     HELPERS
  ================================= */

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

    return number.toLocaleString("en-US");
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


  function escapeHTML(value) {

    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

});