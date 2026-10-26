const BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8200").replace(/\/$/, "");

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const detail = body && body.detail !== undefined ? body.detail : body;
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
    const err = new Error(msg || `HTTP ${res.status}`);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return body;
}

export const api = {
  base: BASE,
  health: () => req("/health"),
  listFiles: ({ page = 1, pageSize = 10, search = "" } = {}) => {
    const q = new URLSearchParams({ page, page_size: pageSize });
    if (search) q.set("search", search);
    return req(`/files?${q.toString()}`);
  },
  getFile: (id) => req(`/files/${id}`),
  updateFile: (id, updatedExtractedValues) =>
    req(`/files/${id}`, { method: "PUT", body: JSON.stringify({ updatedExtractedValues }) }),
  deleteFile: (id) => req(`/files/${id}`, { method: "DELETE" }),
  proceed: (id, opts = {}) =>
    req(`/files/${id}/proceed`, { method: "POST", body: JSON.stringify(opts) }),
};
