import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Detail from "./Detail.jsx";

const PAGE_SIZE = 10;
const POLL_MS = 15000;

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  }).replace(",", " |");
}

function StatusBadge({ status }) {
  const ok = /complete|succeed|created/i.test(status || "");
  const err = /fail|error/i.test(status || "");
  return <span className={`badge ${ok ? "ok" : err ? "err" : "muted"}`}>{status || "—"}</span>;
}

function AweryBadge({ status }) {
  if (!status) return <span className="badge muted">not sent</span>;
  const map = { created: "ok", failed: "err", pending: "warn" };
  return <span className={`badge ${map[status] || "muted"}`}>Awery: {status}</span>;
}

export default function App() {
  const [data, setData] = useState({ items: [], total: 0, total_pages: 1 });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [openIdx, setOpenIdx] = useState(-1);
  const [toast, setToast] = useState(null);
  const pollRef = useRef(null);

  const showToast = useCallback((msg, kind = "") => {
    setToast({ msg, kind });
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => setToast(null), 4000);
  }, []);

  const load = useCallback(async (opts = {}) => {
    const p = opts.page ?? page;
    const s = opts.search ?? search;
    if (!opts.silent) setLoading(true);
    try {
      const res = await api.listFiles({ page: p, pageSize: PAGE_SIZE, search: s });
      setData(res);
      setErr("");
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { load(); }, [page, search]);

  // auto-refresh so new emails appear while running
  useEffect(() => {
    pollRef.current = setInterval(() => {
      if (openIdx < 0) load({ silent: true });
    }, POLL_MS);
    return () => clearInterval(pollRef.current);
  }, [load, openIdx]);

  const items = data.items || [];
  const openDoc = openIdx >= 0 ? items[openIdx] : null;

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <span className="logo">✈️</span> MIXJET
          <span className="sep">›</span>
          <span className="page">Aviation Permit Requests</span>
          <span className="count-pill">{data.total}</span>
        </div>
        <span className="spacer" />
        <form
          className="search"
          onSubmit={(e) => { e.preventDefault(); setPage(1); setSearch(searchInput.trim()); }}
        >
          <span>🔍</span>
          <input
            placeholder="Search file or customer…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          {search && (
            <button type="button" className="btn ghost" onClick={() => { setSearchInput(""); setSearch(""); setPage(1); }}>✕</button>
          )}
        </form>
        <button className="btn" onClick={() => load()} title="Refresh">⟳ Refresh</button>
      </div>

      <div className="card">
        {err && <div className="empty" style={{ color: "var(--err-fg)" }}>⚠ {err}<br /><span className="hint">Is the awery-backend running on {api.base}?</span></div>}
        {!err && (
          <table>
            <thead>
              <tr>
                <th className="row-num">#</th>
                <th>File Name</th>
                <th>Status</th>
                <th>Uploaded At</th>
                <th>Extracted results</th>
                <th>Awery</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={6} className="loading">Loading…</td></tr>}
              {!loading && !items.length && <tr><td colSpan={6} className="empty">No permit requests yet. New emails appear here automatically.</td></tr>}
              {!loading && items.map((it, i) => (
                <tr key={it.id} onClick={() => setOpenIdx(i)}>
                  <td className="row-num">{(page - 1) * PAGE_SIZE + i + 1}</td>
                  <td><span className="file-chip" title={it.file_name}>{it.file_name}</span></td>
                  <td><StatusBadge status={it.status} /></td>
                  <td className="time">{fmtTime(it.uploaded_at)}</td>
                  <td><div className="summary" title={it.extracted_summary}>{it.extracted_summary || <span className="hint">—</span>}</div></td>
                  <td><AweryBadge status={it.awery_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="pager">
          <span className="hint" style={{ marginRight: "auto" }}>
            Page {data.page} of {data.total_pages} · {data.total} total
          </span>
          <button className="pg" disabled={page <= 1} onClick={() => setPage(1)}>«</button>
          <button className="pg" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹</button>
          <span className="pg active">{page}</span>
          <button className="pg" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>›</button>
          <button className="pg" disabled={page >= data.total_pages} onClick={() => setPage(data.total_pages)}>»</button>
        </div>
      </div>

      {openDoc && (
        <Detail
          fileId={openDoc.id}
          onClose={() => setOpenIdx(-1)}
          onPrev={() => setOpenIdx((i) => Math.max(0, i - 1))}
          onNext={() => setOpenIdx((i) => Math.min(items.length - 1, i + 1))}
          hasPrev={openIdx > 0}
          hasNext={openIdx < items.length - 1}
          onChanged={() => load({ silent: true })}
          toast={showToast}
        />
      )}

      {toast && <div className={`toast ${toast.kind}`}>{toast.msg}</div>}
    </div>
  );
}
