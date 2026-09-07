let toastTimer = null;

export function showToast(message, kind = "info", opts = {}) {
    const el = document.getElementById("toast");
    el.textContent = message;
    el.className = "toast" + (kind === "error" ? " toast-error" : kind === "success" ? " toast-success" : "");
    el.hidden = false;
    clearTimeout(toastTimer);
    if (!opts.persist) {
        toastTimer = setTimeout(() => {
            el.hidden = true;
        }, 3500);
    }
}

export function showError(err) {
    const message = err?.detail || err?.message || "Something went wrong. Please try again.";
    showToast(message, "error");
}

/** Shows exactly one of #view-auth / #view-pending / #view-app. */
export function showRoot(name) {
    document.getElementById("view-auth").hidden = name !== "auth";
    document.getElementById("view-pending").hidden = name !== "pending";
    document.getElementById("view-app").hidden = name !== "app";
}

export function showAuthForm(name) {
    document.getElementById("form-login").hidden = name !== "login";
    document.getElementById("form-register").hidden = name !== "register";
}

const TAB_IDS = [
    "today", "history", "profile",
    "admin-today", "admin-pending", "admin-monthly", "admin-history",
];

export function showTab(tabName) {
    for (const id of TAB_IDS) {
        const panel = document.getElementById(`tab-${id}`);
        if (panel) panel.hidden = id !== tabName;
    }
    for (const btn of document.querySelectorAll("[data-tab]")) {
        const isActive = btn.dataset.tab === tabName;
        btn.classList.toggle("active", isActive);
        if (btn.classList.contains("nav-item")) {
            if (isActive) btn.setAttribute("aria-current", "page");
            else btn.removeAttribute("aria-current");
        }
    }
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

export function setButtonLoading(btn, loading, loadingText) {
    if (loading) {
        btn.dataset.originalText = btn.textContent;
        if (loadingText) btn.textContent = loadingText;
        btn.disabled = true;
    } else {
        if (btn.dataset.originalText) btn.textContent = btn.dataset.originalText;
        btn.disabled = false;
    }
}

export function initials(name) {
    return (name || "")
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0].toUpperCase())
        .join("");
}

export function formatMonthInput(date = new Date()) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function formatDateInput(date = new Date()) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function formatFriendlyDate(isoDate) {
    const d = new Date(`${isoDate}T00:00:00`);
    return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
}

export function formatShortDate(isoDate) {
    const d = new Date(`${isoDate}T00:00:00`);
    return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}