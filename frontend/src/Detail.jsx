import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

const SCALAR_ORDER = [
  "Customer Type", "Customer", "Operator", "Flight Type",
  "Purposes", "Reg No", "ACFT Type", "Bulk Reg No",
];

const isTable = (v) => v && typeof v === "object" && v.fieldType === "table";
const isScalar = (v) => v === null || typeof v === "string" || typeof v === "number";

function splitFields(ev) {
  const scalars = [];
  const tables = [];
  const seen = new Set();
  for (const key of SCALAR_ORDER) {
    if (key in ev && isScalar(ev[key])) { scalars.push(key); seen.add(key); }
  }
  for (const [key, val] of Object.entries(ev)) {
    if (seen.has(key)) continue;
    if (isTable(val)) tables.push(key);
    else if (isScalar(val)) scalars.push(key);
  }
  return { scalars, tables };
}

function SubTable({ name, table }) {
  const rows = (table && table.items) || [];
  const cols = rows.length ? Object.keys(rows[0]) : [];
  return (
    <div>
      <div className="section-title">{name}</div>
      <div className="subtable">
        <table>
          <thead>
            <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>{cols.map((c) => <td key={c}>{String(r[c] ?? "")}</td>)}</tr>
            ))}
            {!rows.length && <tr><td className="hint">no rows</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    created: "ok", Completed: "ok", ok: "ok",
    failed: "err", error: "err",
    pending: "warn", dry_run: "muted",
  };
  return <span className={`badge ${map[status] || "muted"}`}>{status || "—"}</span>;
}

export default function Detail({ fileId, onClose, onPrev, onNext, hasPrev, hasNext, onChanged, toast }) {
  const [doc, setDoc] = useState(null);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // proceed options
  const [company, setCompany] = useState("Awery Demo Company");
  const [skipDup, setSkipDup] = useState(true);
  const [createCustomer, setCreateCustomer] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [result, setResult] = useState(null);
  const [showJson, setShowJson] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setResult(null);
    api.getFile(fileId)
      .then((d) => {
        if (!alive) return;
        setDoc(d);
        // Only ever read/edit updatedExtractedValues. extractedValues is the
        // AI's untouched original — a log — and is never shown or written.
        const ev = d.updatedExtractedValues || {};
        setForm(JSON.parse(JSON.stringify(ev)));
      })
      .catch((e) => toast(e.message, "err"))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [fileId]);

  const { scalars, tables } = useMemo(() => splitFields(form || {}), [form]);

  const setScalar = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    setBusy(true);
    try {
      const updated = await api.updateFile(fileId, form);
      setDoc(updated);
      toast("Extraction values updated", "ok");
      onChanged && onChanged();
    } catch (e) {
      toast(e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function runProceed() {
    setBusy(true);
    setResult(null);
    try {
      const opts = {
        dry_run: dryRun,
        create_customer: createCustomer,
        company_name: company || null,
        unique: skipDup ? [0] : null,
      };
      const r = await api.proceed(fileId, opts);
      setResult(r);
      toast(
        dryRun ? "Dry run: payload built (nothing sent)"
        : `Flight created in Awery — id ${r?.awery?.flight_id ?? "?"}`,
        "ok"
      );
      onChanged && onChanged();
      if (!dryRun) {
        const fresh = await api.getFile(fileId);
        setDoc(fresh);
      }
    } catch (e) {
      const d = e.detail;
      setResult(d && typeof d === "object" ? d : { error: e.message });
      toast(typeof d === "object" && d.message ? d.message : e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  const awery = doc?.awery;

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="detail">
        <div className="detail-head">
          <button className="btn" onClick={onPrev} disabled={!hasPrev}>‹ Prev</button>
          <button className="btn" onClick={onNext} disabled={!hasNext}>Next ›</button>
          <span className="title">{doc?.fileName || "…"}</span>
          {awery && <StatusBadge status={awery.status} />}
          <span className="spacer" />
          <button className="btn primary" onClick={runProceed} disabled={busy || loading}>
            Proceed →
          </button>
          <button className="btn" onClick={save} disabled={busy || loading}>Update</button>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>

        <div className="detail-body">
          {/* LEFT — extraction form */}
          <div className="pane">
            <div className="pane-head">
              <h3>Extraction Results</h3>
              <span className="spacer" />
              <span className="hint">edit scalar fields, then Update or Proceed</span>
            </div>
            <div className="pane-scroll">
              {loading && <div className="loading">Loading…</div>}
              {!loading && scalars.map((k) => {
                const long = k === "Purposes" || (typeof form[k] === "string" && form[k].length > 60);
                return (
                  <div className="field" key={k}>
                    <label>{k}</label>
                    {long
                      ? <textarea rows={3} value={form[k] ?? ""} onChange={(e) => setScalar(k, e.target.value)} />
                      : <input value={form[k] ?? ""} onChange={(e) => setScalar(k, e.target.value)} />}
                  </div>
                );
              })}
              {!loading && tables.map((k) => <SubTable key={k} name={k} table={form[k]} />)}
            </div>
          </div>

          {/* RIGHT — pdf + proceed */}
          <div className="pane">
            <div className="pane-head">
              <h3>Source Document</h3>
              <span className="spacer" />
              {doc?.originalFile && (
                <a className="btn" href={doc.originalFile} target="_blank" rel="noreferrer">Open PDF ↗</a>
              )}
            </div>
            <div style={{ flex: 1, minHeight: 0 }}>
              {doc?.originalFile
                ? <iframe className="pdf" title="pdf" src={doc.originalFile} />
                : <div className="empty">No document</div>}
            </div>

            <div className="result">
              <h4>Send to Awery ERP</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", margin: "6px 0 10px" }}>
                <label className="field" style={{ margin: 0, flex: "1 1 220px" }}>
                  <label>Awery company (company__name)</label>
                  <input value={company} onChange={(e) => setCompany(e.target.value)} />
                </label>
                <label className="hint"><input type="checkbox" checked={skipDup} onChange={(e) => setSkipDup(e.target.checked)} /> skip duplicate check</label>
                <label className="hint"><input type="checkbox" checked={createCustomer} onChange={(e) => setCreateCustomer(e.target.checked)} /> create customer first</label>
                <label className="hint"><input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} /> dry run</label>
              </div>

              {awery && !result && (
                <div className="kv">
                  <span className="k">last run</span><span><StatusBadge status={awery.status} /> {awery.processed_at}</span>
                  {awery.flight_id && (<><span className="k">Awery flight_id</span><span>{awery.flight_id}</span></>)}
                  {awery.flight_no && (<><span className="k">flight_no</span><span>{awery.flight_no}</span></>)}
                  {awery.error && (<><span className="k">error</span><span style={{ color: "var(--err-fg)" }}>{awery.error}</span></>)}
                </div>
              )}

              {result && (
                <>
                  <div className="kv">
                    <span className="k">mode</span><span>{result.dry_run ? "dry run (nothing sent)" : "live createFlight"}</span>
                    {result.awery && (<><span className="k">status</span><span><StatusBadge status={result.awery.status} /></span></>)}
                    {result.awery?.flight_id && (<><span className="k">Awery flight_id</span><span><b>{result.awery.flight_id}</b></span></>)}
                    {result.awery?.flight_no && (<><span className="k">flight_no</span><span>{result.awery.flight_no}</span></>)}
                    {result.error && (<><span className="k">error</span><span style={{ color: "var(--err-fg)" }}>{String(result.error)}</span></>)}
                    {result.message && (<><span className="k">message</span><span style={{ color: "var(--err-fg)" }}>{result.message}</span></>)}
                  </div>
                  <button className="btn ghost" style={{ padding: "4px 0" }} onClick={() => setShowJson((s) => !s)}>
                    {showJson ? "▾ hide" : "▸ show"} payload / response JSON
                  </button>
                  {showJson && <pre className="json">{JSON.stringify(result, null, 2)}</pre>}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
