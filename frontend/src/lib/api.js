const BASE = "/api";

function getAuthHeaders(options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = localStorage.getItem("planetmind_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: getAuthHeaders(options),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function apiUpload(path, formData) {
  const token = localStorage.getItem("planetmind_token");
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    body: formData,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}
