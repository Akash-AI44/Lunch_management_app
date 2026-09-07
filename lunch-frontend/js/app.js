import { authApi, employeeApi, adminApi, getToken, setToken, clearToken, ApiError } from "./api.js";
import {
    showToast, showError, showRoot, showAuthForm, showTab, setButtonLoading,
    initials, formatMonthInput, formatDateInput, formatFriendlyDate, formatShortDate,
} from "./ui.js";

// ---------------------------------------------------------------------
// App state
// ---------------------------------------------------------------------
let currentUser = null; // { id, name, email, role, status, profile_picture_url, ... }

/** Warns loudly, on load, if the API_BASE clearly can't work from this
 * device — e.g. the page was opened via a LAN IP (like a phone would)
 * but API_BASE still points at 127.0.0.1, which means "this device"
 * to whoever's loading the page, not your computer. */
function warnIfApiBaseLooksWrong() {
    const apiBase = window.__API_BASE__ || "";
    const pageHost = location.hostname;
    const pageIsLocal = pageHost === "127.0.0.1" || pageHost === "localhost";
    const apiIsLocal = apiBase.includes("127.0.0.1") || apiBase.includes("localhost");

    if (!pageIsLocal && apiIsLocal) {
        showToast(
            `This page was opened via ${pageHost}, but js/config.js still points the API at 127.0.0.1 — that means "this device" to whoever loads the page, not your computer. Update API_BASE to your computer's LAN IP.`,
            "error",
            { persist: true }
        );
    }
}

// ---------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------
async function boot() {
    warnIfApiBaseLooksWrong();
    wireAuthForms();
    wireGoogleSignIn();
    wirePendingScreen();
    wireNav();
    wireEmployeeToday();
    wireHistory();
    wireProfile();
    wireAdminPending();
    wireAdminToday();
    wireAdminMonthly();
    wireAdminHistory();

    const token = getToken();
    if (!token) {
        showRoot("auth");
        return;
    }

    try {
        currentUser = await authApi.me();
        await routeAfterAuth();
    } catch (err) {
        clearToken();
        showRoot("auth");
    }
}

async function routeAfterAuth() {
    if (currentUser.status !== "active") {
        showRoot("pending");
        return;
    }
    showRoot("app");
    setupNavForRole();
    renderNavUser();
    if (currentUser.role === "superadmin") {
        showTab("admin-today");
        await loadAdminToday();
        await loadCutoffSettings(); // once per session, not on every tab/date change — see loadCutoffSettings()
    } else {
        showTab("today");
        await loadEmployeeToday();
        await loadEmployeeSummary();
    }
}

function setupNavForRole() {
    const isAdmin = currentUser.role === "superadmin";
    document.getElementById("nav-employee").hidden = isAdmin;
    document.getElementById("nav-admin").hidden = !isAdmin;
    document.getElementById("bottom-nav-employee").hidden = isAdmin;
    document.getElementById("bottom-nav-admin").hidden = !isAdmin;
}

function renderNavUser() {
    document.getElementById("nav-user").textContent = currentUser.name;
}

// ---------------------------------------------------------------------
// Auth forms
// ---------------------------------------------------------------------
function wireAuthForms() {
    document.querySelectorAll("[data-show]").forEach((btn) => {
        btn.addEventListener("click", () => showAuthForm(btn.dataset.show));
    });

    const loginForm = document.getElementById("form-login");
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = loginForm.querySelector("button[type=submit]");
        const data = new FormData(loginForm);
        setButtonLoading(btn, true, "Signing in…");
        try {
            const { access_token } = await authApi.login(data.get("email"), data.get("password"));
            setToken(access_token);
            currentUser = await authApi.me();
            loginForm.reset();
            await routeAfterAuth();
        } catch (err) {
            showError(err);
        } finally {
            setButtonLoading(btn, false);
        }
    });

    const registerForm = document.getElementById("form-register");
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = registerForm.querySelector("button[type=submit]");
        const data = new FormData(registerForm);
        setButtonLoading(btn, true, "Creating account…");
        try {
            await authApi.register(data.get("name"), data.get("email"), data.get("password"), data.get("phone_number"));
            const { access_token } = await authApi.login(data.get("email"), data.get("password"));
            setToken(access_token);
            currentUser = await authApi.me();
            registerForm.reset();
            await routeAfterAuth();
        } catch (err) {
            showError(err);
        } finally {
            setButtonLoading(btn, false);
        }
    });
}

// ---------------------------------------------------------------------
// Google Sign-In (Google Identity Services)
// ---------------------------------------------------------------------
function wireGoogleSignIn() {
    const clientId = window.__GOOGLE_CLIENT_ID__ || "";
    if (!clientId) {
        // Not configured — leave the button slots empty and the divider
        // hidden (both already start hidden/empty in the HTML). Nothing
        // else to do; email/password sign-in still works normally.
        return;
    }

    // The GSI script tag is loaded with `defer`, so it may not have run
    // yet by the time our own module executes. Poll briefly rather than
    // assuming `google` exists immediately.
    const tryInit = (attemptsLeft) => {
        if (window.google?.accounts?.id) {
            initGoogleButton(clientId);
            return;
        }
        if (attemptsLeft <= 0) {
            console.warn("Google Identity Services script did not load — Google Sign-In will be unavailable.");
            return;
        }
        setTimeout(() => tryInit(attemptsLeft - 1), 300);
    };
    tryInit(20); // ~6 seconds total
}

function initGoogleButton(clientId) {
    window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCredential,
    });

    const loginSlot = document.getElementById("google-signin-login");
    const registerSlot = document.getElementById("google-signin-register");
    const buttonOptions = { theme: "outline", size: "large", width: 280, text: "continue_with" };

    window.google.accounts.id.renderButton(loginSlot, buttonOptions);
    window.google.accounts.id.renderButton(registerSlot, buttonOptions);

    document.getElementById("google-signin-divider").hidden = false;
    document.getElementById("google-signin-divider-register").hidden = false;
}

async function handleGoogleCredential(response) {
    try {
        const { access_token } = await authApi.googleLogin(response.credential);
        setToken(access_token);
        currentUser = await authApi.me();
        await routeAfterAuth();
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
// Pending (awaiting activation) screen
// ---------------------------------------------------------------------
function wirePendingScreen() {
    document.getElementById("btn-pending-refresh").addEventListener("click", async (e) => {
        setButtonLoading(e.target, true, "Checking…");
        try {
            currentUser = await authApi.me();
            if (currentUser.status === "active") {
                showToast("You're activated — welcome in!", "success");
            } else {
                showToast("Still pending — check back soon.");
            }
            await routeAfterAuth();
        } catch (err) {
            showError(err);
        } finally {
            setButtonLoading(e.target, false);
        }
    });

    document.getElementById("btn-pending-logout").addEventListener("click", logout);
}

function logout() {
    clearToken();
    currentUser = null;
    showRoot("auth");
    showAuthForm("login");
}

// ---------------------------------------------------------------------
// Nav (side nav + bottom nav share the same data-tab buttons)
// ---------------------------------------------------------------------
function wireNav() {
    document.getElementById("btn-logout").addEventListener("click", logout);
    // Mirrors #btn-logout, but reachable on mobile too — the side-nav (and
    // its sign-out link) is hidden entirely below the desktop breakpoint,
    // so the bottom-nav-reachable Profile tab needs its own sign-out control.
    document.getElementById("btn-profile-logout").addEventListener("click", logout);

    document.querySelectorAll("[data-tab]").forEach((btn) => {
        btn.addEventListener("click", () => onTabSelected(btn.dataset.tab));
    });
}

async function onTabSelected(tab) {
    showTab(tab);
    try {
        if (tab === "today") await loadEmployeeToday();
        else if (tab === "history") await loadHistory();
        else if (tab === "profile") renderProfile();
        else if (tab === "admin-today") await loadAdminToday();
        else if (tab === "admin-pending") await loadAdminPending();
        else if (tab === "admin-monthly") await loadAdminMonthly();
        else if (tab === "admin-history") await loadAdminHistory();
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
// Employee: Today
// ---------------------------------------------------------------------
function wireEmployeeToday() {
    document.getElementById("today-toggle").addEventListener("click", async () => {
        const btn = document.getElementById("today-toggle");
        const currentlyOn = btn.getAttribute("aria-pressed") === "true";
        btn.disabled = true;
        try {
            const status = await employeeApi.updateToday(!currentlyOn);
            renderTodayStatus(status);
            await loadEmployeeSummary();
        } catch (err) {
            showError(err);
        } finally {
            btn.disabled = false;
        }
    });
}

async function loadEmployeeToday() {
    document.getElementById("today-date").textContent = formatFriendlyDate(formatDateInput());
    document.getElementById("today-greeting").textContent = `Hi, ${currentUser.name.split(" ")[0]}`;
    try {
        const status = await employeeApi.today();
        renderTodayStatus(status);
    } catch (err) {
        showError(err);
    }
}

function renderTodayStatus(status) {
    const label = document.getElementById("today-status");
    const note = document.getElementById("today-note");
    const toggle = document.getElementById("today-toggle");

    label.classList.remove("is-on", "is-off", "is-wait");

    if (status.day_type === "weekend") {
        label.textContent = "It's the weekend";
        label.classList.add("is-wait");
        note.textContent = status.message || "No lunch feature on Saturdays and Sundays.";
        toggle.hidden = true;
        return;
    }
    toggle.hidden = false;

    const isOn = !!status.is_having_lunch;
    toggle.setAttribute("aria-pressed", String(isOn));
    toggle.disabled = status.locked;

    label.textContent = isOn ? "You're getting lunch" : status.day_type === "friday" ? "Default: no lunch (WFH)" : "You've opted out";
    label.classList.add(isOn ? "is-on" : "is-off");

    if (status.locked) {
        note.textContent = `The ${status.cutoff_time} cutoff has passed — today is locked.`;
    } else if (status.day_type === "friday") {
        note.textContent = isOn
            ? `Coming in — checked in before ${status.cutoff_time}.`
            : `Coming in today? Check the box before ${status.cutoff_time}.`;
    } else {
        note.textContent = `Uncheck before ${status.cutoff_time} to skip.`;
    }
}

async function loadEmployeeSummary() {
    const month = formatMonthInput();
    try {
        const summary = await employeeApi.summary(month);
        document.getElementById("stat-lunches").textContent = summary.total_lunches;
        document.getElementById("stat-skipped").textContent = summary.total_skipped;
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
// Employee: History
// ---------------------------------------------------------------------
function wireHistory() {
    const monthInput = document.getElementById("history-month");
    monthInput.value = formatMonthInput();
    monthInput.addEventListener("change", loadHistory);
}

async function loadHistory() {
    const month = document.getElementById("history-month").value || formatMonthInput();
    const list = document.getElementById("history-list");
    const empty = document.getElementById("history-empty");
    list.innerHTML = "";
    try {
        const rows = await employeeApi.history(month);
        empty.hidden = rows.length > 0;
        for (const row of rows) {
            const li = document.createElement("li");
            const isOn = !!row.is_having_lunch;
            li.innerHTML = `
        <span class="row-title">${formatShortDate(row.date)}</span>
        <span class="row-status ${isOn ? "is-on" : "is-off"}">${isOn ? "Had lunch" : row.day_type === "friday" ? "WFH" : "Skipped"}</span>
      `;
            list.appendChild(li);
        }
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
// Profile (employee + admin)
// ---------------------------------------------------------------------
function wireProfile() {
    const avatarInput = document.getElementById("profile-avatar-input");
    document.getElementById("profile-avatar-fallback").parentElement.addEventListener("click", () => avatarInput.click());
    avatarInput.addEventListener("change", async () => {
        const file = avatarInput.files[0];
        if (!file) return;
        try {
            currentUser = await employeeApi.uploadAvatar(file);
            renderProfile();
            renderNavUser();
            showToast("Profile picture updated.", "success");
        } catch (err) {
            showError(err);
        } finally {
            avatarInput.value = "";
        }
    });

    const pwForm = document.getElementById("form-change-password");
    pwForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = pwForm.querySelector("button[type=submit]");
        const data = new FormData(pwForm);
        setButtonLoading(btn, true, "Updating…");
        try {
            await authApi.changePassword(data.get("current_password"), data.get("new_password"));
            pwForm.reset();
            showToast("Password updated.", "success");
        } catch (err) {
            showError(err);
        } finally {
            setButtonLoading(btn, false);
        }
    });
}

function renderProfile() {
    document.getElementById("profile-name").textContent = currentUser.name;
    document.getElementById("profile-email").textContent = currentUser.email;
    document.getElementById("profile-role").textContent = currentUser.role === "superadmin" ? "Superadmin" : "Employee";

    const img = document.getElementById("profile-avatar-img");
    const fallback = document.getElementById("profile-avatar-fallback");
    if (currentUser.profile_picture_url) {
        img.src = currentUser.profile_picture_url;
        img.hidden = false;
        fallback.hidden = true;
    } else {
        img.hidden = true;
        fallback.hidden = false;
        fallback.textContent = initials(currentUser.name);
    }
}

// ---------------------------------------------------------------------
// Admin: Today
// ---------------------------------------------------------------------
function wireAdminToday() {
    const dateInput = document.getElementById("admin-today-date-input");
    dateInput.value = formatDateInput();
    dateInput.addEventListener("change", loadAdminToday);
    document.getElementById("btn-export-csv").addEventListener("click", exportCsv);
    document.getElementById("btn-update-cutoff").addEventListener("click", updateCutoff);
}

async function loadAdminToday() {
    const on = document.getElementById("admin-today-date-input").value || formatDateInput();
    document.getElementById("admin-today-date").textContent = formatFriendlyDate(on);
    try {
        const data = await adminApi.daily(on);
        document.getElementById("admin-daily-count").textContent = data.total_having_lunch;
        document.getElementById("admin-daily-label").textContent =
            data.day_type === "weekend" ? "Weekend — no lunch" : data.day_type === "friday" ? "Opted in (Friday)" : "Getting lunch";

        const list = document.getElementById("admin-daily-names");
        const empty = document.getElementById("admin-daily-empty");
        list.innerHTML = "";
        empty.hidden = data.names.length > 0;
        for (const name of data.names) {
            const li = document.createElement("li");
            li.innerHTML = `<span class="row-title">${name}</span>`;
            list.appendChild(li);
        }
    } catch (err) {
        showError(err);
    }
}

/** Loaded once per admin session (see routeAfterAuth), NOT re-run every
 * time the Today tab is opened or the date changes — loadAdminToday()
 * fires far more often than that, and if this lived inside it, a
 * late-resolving fetch could silently overwrite whatever cutoff value
 * the admin had already started typing. It's also refreshed after a
 * successful update, from the response, rather than by re-fetching. */
async function loadCutoffSettings() {
    try {
        const settings = await adminApi.getSettings();
        const timeInput = document.getElementById("cutoff-time-input");
        timeInput.value = `${String(settings.cutoff_hour).padStart(2, "0")}:${String(settings.cutoff_minute).padStart(2, "0")}`;
    } catch (err) {
        showError(err);
    }
}

async function updateCutoff() {
    const btn = document.getElementById("btn-update-cutoff");
    const value = document.getElementById("cutoff-time-input").value; // "HH:MM"
    if (!value) {
        showToast("Pick a time first.", "error");
        return;
    }
    const [hour, minute] = value.split(":").map((n) => parseInt(n, 10));
    setButtonLoading(btn, true, "Updating…");
    try {
        const settings = await adminApi.updateSettings(hour, minute);
        document.getElementById("cutoff-time-input").value =
            `${String(settings.cutoff_hour).padStart(2, "0")}:${String(settings.cutoff_minute).padStart(2, "0")}`;
        showToast(`Cutoff updated to ${settings.cutoff_label}. Employees can act on this immediately.`, "success");
    } catch (err) {
        showError(err);
    } finally {
        setButtonLoading(btn, false);
    }
}

async function exportCsv() {
    const btn = document.getElementById("btn-export-csv");
    const on = document.getElementById("admin-today-date-input").value || formatDateInput();
    setButtonLoading(btn, true, "Exporting…");
    try {
        const blob = await adminApi.exportCsv(on);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `lunch-list-${on}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (err) {
        showError(err);
    } finally {
        setButtonLoading(btn, false);
    }
}

// ---------------------------------------------------------------------
// Admin: Pending registrations
// ---------------------------------------------------------------------
function wireAdminPending() {
    // Delegated: buttons are rendered dynamically.
    document.getElementById("admin-pending-list").addEventListener("click", async (e) => {
        const btn = e.target.closest("button[data-action]");
        if (!btn) return;
        const userId = btn.dataset.userId;
        const action = btn.dataset.action;
        btn.disabled = true;
        try {
            if (action === "activate") await adminApi.activate(userId);
            else await adminApi.reject(userId);
            showToast(action === "activate" ? "Employee activated." : "Registration rejected.", "success");
            await loadAdminPending();
        } catch (err) {
            showError(err);
            btn.disabled = false;
        }
    });
}

async function loadAdminPending() {
    const list = document.getElementById("admin-pending-list");
    const empty = document.getElementById("admin-pending-empty");
    const badge = document.getElementById("pending-badge");
    list.innerHTML = "";
    try {
        const users = await adminApi.pending();
        empty.hidden = users.length > 0;
        badge.hidden = users.length === 0;
        if (users.length) badge.textContent = users.length;

        for (const u of users) {
            const li = document.createElement("li");
            li.innerHTML = `
        <div>
          <p class="row-title">${u.name}</p>
          <p class="row-sub">${u.email}</p>
        </div>
        <div class="pill-actions">
          <button class="pill-btn pill-btn-accept" data-action="activate" data-user-id="${u.id}">Activate</button>
          <button class="pill-btn pill-btn-reject" data-action="reject" data-user-id="${u.id}">Reject</button>
        </div>
      `;
            list.appendChild(li);
        }
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
// Admin: Monthly totals
// ---------------------------------------------------------------------
function wireAdminMonthly() {
    const monthInput = document.getElementById("admin-monthly-month");
    monthInput.value = formatMonthInput();
    monthInput.addEventListener("change", loadAdminMonthly);
}

async function loadAdminMonthly() {
    const month = document.getElementById("admin-monthly-month").value || formatMonthInput();
    const body = document.getElementById("admin-monthly-body");
    const empty = document.getElementById("admin-monthly-empty");
    body.innerHTML = "";
    try {
        const data = await adminApi.monthly(month);
        empty.hidden = data.employees.length > 0;
        for (const e of data.employees) {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${e.name}</td><td>${e.email}</td><td class="num">${e.total_lunches}</td>`;
            body.appendChild(tr);
        }
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
// Admin: Monthly calendar + day drilldown
// ---------------------------------------------------------------------
function wireAdminHistory() {
    const monthInput = document.getElementById("admin-history-month");
    monthInput.value = formatMonthInput();
    monthInput.addEventListener("change", loadAdminHistory);

    document.getElementById("admin-calendar").addEventListener("click", async (e) => {
        const btn = e.target.closest(".cal-day");
        if (!btn || btn.dataset.daytype === "weekend") return;
        document.querySelectorAll(".cal-day.selected").forEach((el) => el.classList.remove("selected"));
        btn.classList.add("selected");
        await loadDayDrilldown(btn.dataset.date);
    });
}

const DOW_LABELS = ["M", "T", "W", "T", "F", "S", "S"];

async function loadAdminHistory() {
    const month = document.getElementById("admin-history-month").value || formatMonthInput();
    const grid = document.getElementById("admin-calendar");
    document.getElementById("admin-day-drilldown").hidden = true;
    grid.innerHTML = "";

    try {
        const data = await adminApi.history(month);

        for (const label of DOW_LABELS) {
            const el = document.createElement("div");
            el.className = "cal-dow";
            el.textContent = label;
            grid.appendChild(el);
        }

        // Pad so the 1st of the month lands in the right weekday column (Mon-first).
        const firstDate = new Date(`${data.days[0].date}T00:00:00`);
        const leadingBlanks = (firstDate.getDay() + 6) % 7; // convert Sun=0 -> Mon=0 indexing
        for (let i = 0; i < leadingBlanks; i++) {
            grid.appendChild(document.createElement("div"));
        }

        for (const day of data.days) {
            const dayNum = day.date.slice(-2);
            const btn = document.createElement("button");
            btn.className = "cal-day";
            btn.type = "button";
            btn.dataset.date = day.date;
            btn.dataset.daytype = day.day_type;
            btn.innerHTML = `<span class="cal-day-num">${parseInt(dayNum, 10)}</span><span class="cal-day-count">${day.count ?? "–"}</span>`;
            grid.appendChild(btn);
        }
    } catch (err) {
        showError(err);
    }
}

async function loadDayDrilldown(isoDate) {
    const wrap = document.getElementById("admin-day-drilldown");
    const title = document.getElementById("drilldown-title");
    const list = document.getElementById("drilldown-names");
    const empty = document.getElementById("drilldown-empty");

    wrap.hidden = false;
    title.textContent = formatFriendlyDate(isoDate);
    list.innerHTML = "";

    try {
        const data = await adminApi.historyDay(isoDate);
        empty.hidden = data.names.length > 0;
        for (const name of data.names) {
            const li = document.createElement("li");
            li.innerHTML = `<span class="row-title">${name}</span>`;
            list.appendChild(li);
        }
    } catch (err) {
        showError(err);
    }
}

// ---------------------------------------------------------------------
boot();