function bbaColorPick(input, previewId) {
    const preview = document.getElementById(previewId);
    if (preview) {
        preview.style.background = input.value + "22";
        preview.style.color = input.value;
    }
    const swatch = input.closest(".bba-color-swatch");
    if (swatch && swatch.parentElement) {
        swatch.parentElement.querySelectorAll(".bba-color-swatch").forEach((el) => el.classList.remove("selected"));
        swatch.classList.add("selected");
    }
}
