// All talking to the backend happens here, so pages stay simple.
const TOKEN_KEY = "dq_token";
const USER_KEY = "dq_user";

export const session = {
  token: () => localStorage.getItem(TOKEN_KEY),
  user: () => {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
  },
  save: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  saveUser: (user) => localStorage.setItem(USER_KEY, JSON.stringify(user)),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

// FastAPI sends errors as {detail: "text"} or {detail: [{msg: "..."}]}
function errorText(body, fallback) {
  if (!body || !body.detail) return fallback;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => (d.msg || "").replace(/^Value error, /, "")).join(" ") || fallback;
  }
  return fallback;
}

async function request(path, { method = "GET", json, form, raw } = {}) {
  const headers = {};
  const token = session.token();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form; // the browser sets the multipart header itself
  }

  let response;
  try {
    response = await fetch(`/api${path}`, { method, headers, body });
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }

  if (response.status === 401 && token) onUnauthorized();
  if (!response.ok) {
    let parsed = null;
    try { parsed = await response.json(); } catch { /* not JSON */ }
    throw new Error(errorText(parsed, `Request failed (${response.status}).`));
  }
  if (response.status === 204) return null;
  return raw ? response : response.json();
}

export const api = {
  signup: (data) => request("/auth/signup", { method: "POST", json: data }),
  login: (data) => request("/auth/login", { method: "POST", json: data }),
  updateSettings: (data) => request("/auth/me", { method: "PATCH", json: data }),

  listDatasets: () => request("/datasets"),
  trends: () => request("/datasets/trends"),
  getDataset: (id) => request(`/datasets/${id}`),
  deleteDataset: (id) => request(`/datasets/${id}`, { method: "DELETE" }),
  uploadSample: () => request("/datasets/sample", { method: "POST" }),
  upload: (file, rules) => {
    const form = new FormData();
    form.append("file", file);
    if (rules && Object.keys(rules).length) form.append("rules", JSON.stringify(rules));
    return request("/datasets", { method: "POST", form });
  },
  issues: (id, params) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
    return request(`/datasets/${id}/issues?${query}`);
  },
  preview: (id, rows) => request(`/datasets/${id}/preview?rows=${rows}`),

  // Downloads need the login token, so we fetch the file and then save it.
  downloadCleaned: async (id) => {
    const response = await request(`/datasets/${id}/cleaned`, { raw: true });
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = match ? match[1] : "cleaned.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  },
};
