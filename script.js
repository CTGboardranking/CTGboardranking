const themeBtn = document.getElementById("themeBtn");

const savedTheme = localStorage.getItem("ctg-theme");

if (savedTheme === "dark") {
    document.body.classList.add("dark");
}

themeBtn.addEventListener("click", () => {

    document.body.classList.toggle("dark");

    const dark =
        document.body.classList.contains("dark");

    localStorage.setItem(
        "ctg-theme",
        dark ? "dark" : "light"
    );
});
