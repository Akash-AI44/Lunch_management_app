// Same-origin by default (the FastAPI app serves this frontend at /app).
// Override by setting window.__API_BASE__ before this script loads if
// you ever host the frontend separately from the API.
const API_BASE = window.__API_BASE__ || "";

const TOKEN_KEY = "lunch_club_token";

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `Request failed (${status})`);
        this.status = status;
        this.detail = detail;
    }
}

async function request(path, { method = "GET", body, isForm = false, isBlob = false } = {}) {
    const headers = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (body && !isForm) headers["Content-Type"] = "application/json";

    const res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    });

    if (!res.ok) {
        let detail = `Request failed (${res.status})`;
        try {
            const data = await res.json();
            if (data?.detail) {
                detail = Array.isArray(data.detail)
                    ? data.detail.map((d) => d.msg).join(", ")
                    : data.detail;
            }
        } catch {
            /* response body wasn't JSON — keep the generic message */
        }
        throw new ApiError(res.status, detail);
    }

    if (res.status === 204) return null;
    if (isBlob) return res.blob();
    return res.json();
}

// ---------- Auth ----------
export const authApi = {
    register: (name, email, password, phone_number) =>
        request("/auth/register", { method: "POST", body: { name, email, password, phone_number: phone_number || undefined } }),
    login: (email, password) =>
        request("/auth/login", { method: "POST", body: { email, password } }),
    googleLogin: (idToken) =>
        request("/auth/google", { method: "POST", body: { id_token: idToken } }),
    me: () => request("/auth/me"),
    changePassword: (current_password, new_password) =>
        request("/auth/change-password", { method: "POST", body: { current_password, new_password } }),
};

// ---------- Employee ----------
export const employeeApi = {
    today: () => request("/employee/today"),
    updateToday: (is_having_lunch) =>
        request("/employee/today", { method: "PATCH", body: { is_having_lunch } }),
    history: (month) => request(`/employee/history?month=${month}`),
    summary: (month) => request(`/employee/summary?month=${month}`),
    uploadAvatar: (file) => {
        const form = new FormData();
        form.append("file", file);
        return request("/employee/profile-picture", { method: "POST", body: form, isForm: true });
    },
};

// ---------- Admin ----------
export const adminApi = {
    pending: () => request("/admin/pending"),
    activate: (userId) => request(`/admin/activate/${userId}`, { method: "POST" }),
    reject: (userId) => request(`/admin/reject/${userId}`, { method: "POST" }),
    daily: (on) => request(`/admin/daily${on ? `?on=${on}` : ""}`),
    monthly: (month) => request(`/admin/monthly?month=${month}`),
    history: (month) => request(`/admin/history?month=${month}`),
    historyDay: (on) => request(`/admin/history/day?on=${on}`),
    exportCsv: (on) => request(`/admin/export${on ? `?on=${on}` : ""}`, { isBlob: true }),
    getSettings: () => request("/admin/settings"),
    updateSettings: (cutoff_hour, cutoff_minute) =>
        request("/admin/settings", { method: "PATCH", body: { cutoff_hour, cutoff_minute } }),
};

export { ApiError, API_BASE };