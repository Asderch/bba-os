const TR_MONTH_NAMES = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];
const TR_DAY_NAMES = ["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz"];

document.addEventListener("DOMContentLoaded", initDatePickers);

function initDatePickers() {
    document.querySelectorAll(".date-field").forEach((field) => {
        const hidden = field.querySelector('input[type="hidden"]');
        const display = field.querySelector(".date-display");
        updateDisplay(hidden, display);
        display.addEventListener("click", (e) => {
            e.stopPropagation();
            const alreadyOpen = field.querySelector(".mini-calendar");
            closeAllCalendars();
            if (!alreadyOpen) openCalendar(field, hidden, display);
        });
    });
    document.addEventListener("click", closeAllCalendars);
}

function updateDisplay(hidden, display) {
    if (!hidden.value) {
        display.textContent = "Tarih seç";
        return;
    }
    const [y, m, d] = hidden.value.split("-").map(Number);
    display.textContent = `${String(d).padStart(2, "0")}.${String(m).padStart(2, "0")}.${y}`;
}

function closeAllCalendars() {
    document.querySelectorAll(".mini-calendar").forEach((el) => el.remove());
}

function openCalendar(field, hidden, display) {
    let [y, m, d] = hidden.value ? hidden.value.split("-").map(Number) : (() => {
        const now = new Date();
        return [now.getFullYear(), now.getMonth() + 1, now.getDate()];
    })();
    let viewYear = y, viewMonth = m;

    const calEl = document.createElement("div");
    calEl.className = "mini-calendar";
    calEl.addEventListener("click", (e) => e.stopPropagation());
    field.appendChild(calEl);
    render();

    function render() {
        calEl.innerHTML = "";

        const header = document.createElement("div");
        header.className = "mini-calendar-header";
        const prevBtn = document.createElement("button");
        prevBtn.type = "button"; prevBtn.className = "mini-calendar-nav"; prevBtn.textContent = "‹";
        const nextBtn = document.createElement("button");
        nextBtn.type = "button"; nextBtn.className = "mini-calendar-nav"; nextBtn.textContent = "›";
        const label = document.createElement("span");
        label.className = "mini-calendar-label";
        label.textContent = `${TR_MONTH_NAMES[viewMonth - 1]} ${viewYear}`;
        prevBtn.onclick = (e) => { e.stopPropagation(); viewMonth--; if (viewMonth < 1) { viewMonth = 12; viewYear--; } render(); };
        nextBtn.onclick = (e) => { e.stopPropagation(); viewMonth++; if (viewMonth > 12) { viewMonth = 1; viewYear++; } render(); };
        header.append(prevBtn, label, nextBtn);
        calEl.appendChild(header);

        const grid = document.createElement("div");
        grid.className = "mini-calendar-grid";
        TR_DAY_NAMES.forEach((dn) => {
            const el = document.createElement("div");
            el.className = "mini-calendar-dayname";
            el.textContent = dn;
            grid.appendChild(el);
        });

        const firstDay = new Date(viewYear, viewMonth - 1, 1);
        let startOffset = (firstDay.getDay() + 6) % 7; // Pazartesi ilk gün olacak şekilde
        const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();

        for (let i = 0; i < startOffset; i++) grid.appendChild(document.createElement("div"));

        for (let day = 1; day <= daysInMonth; day++) {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "mini-calendar-day";
            cell.textContent = day;
            if (day === d && viewMonth === m && viewYear === y) cell.classList.add("mini-calendar-selected");
            cell.onclick = (e) => {
                e.stopPropagation();
                const iso = `${viewYear}-${String(viewMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                hidden.value = iso;
                d = day; m = viewMonth; y = viewYear;
                updateDisplay(hidden, display);
                closeAllCalendars();
            };
            grid.appendChild(cell);
        }
        calEl.appendChild(grid);
    }
}
