from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

import speer_core


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
EXPORT_DIR = OUTPUT_DIR / "exports"

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".xml"}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Speer")

latest_records: list[dict] = []
latest_exports: dict | None = None


HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Speer Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      --bg-start: #0a0f1f;
      --bg-mid: #121833;
      --bg-end: #1a1030;
      --surface: rgba(18, 22, 45, 0.78);
      --surface-strong: rgba(28, 32, 60, 0.92);
      --border: rgba(255, 255, 255, 0.08);
      --glow: rgba(106, 144, 255, 0.12);
      --text-primary: #f5f7ff;
      --text-muted: #a9b2cc;
      --accent: linear-gradient(135deg, #5c7cff, #7b5cff);
      --accent-solid: #6a8cff;
      --success: #2dd4a7;
      --warning: #f3b544;
    }
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(160deg, var(--bg-start) 0%, var(--bg-mid) 50%, var(--bg-end) 100%);
      color: var(--text-primary);
      display: flex;
      justify-content: center;
      padding: 2.5rem 1.5rem 4rem;
    }
    .container {
      width: 100%;
      max-width: 1100px;
      display: flex;
      flex-direction: column;
      gap: 1.75rem;
    }
    nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 0;
    }
    .logo {
      font-size: 1.4rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: lowercase;
    }
    .nav-links {
      display: flex;
      align-items: center;
      gap: 1rem;
      font-size: 0.95rem;
    }
    .nav-links a {
      color: var(--text-muted);
      text-decoration: none;
    }
    .nav-links a:focus-visible,
    .button-primary:focus-visible,
    .button-secondary:focus-visible,
    input[type="file"]:focus-visible {
      outline: 2px solid var(--accent-solid);
      outline-offset: 2px;
      border-radius: 999px;
    }
    .button-primary {
      background: var(--accent);
      color: #ffffff;
      padding: 0.55rem 1.4rem;
      border-radius: 999px;
      font-weight: 700;
      border: none;
      cursor: pointer;
      box-shadow: 0 12px 24px rgba(92, 124, 255, 0.25);
    }
    .hero {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 2rem;
      align-items: center;
    }
    .hero h1 {
      margin: 0 0 0.5rem;
      font-size: clamp(2.6rem, 4vw, 3.4rem);
      font-weight: 700;
    }
    .hero p {
      margin: 0 0 1rem;
      color: var(--text-muted);
      font-size: 1.05rem;
      line-height: 1.6;
    }
    .notice {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 0.85rem 1rem;
      border-radius: 12px;
      color: var(--text-muted);
      font-size: 0.95rem;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 1.5rem;
      backdrop-filter: blur(18px);
      box-shadow: 0 20px 40px rgba(8, 12, 30, 0.4);
    }
    .upload-box {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    input[type="file"] {
      width: 100%;
      padding: 0.85rem;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(10, 14, 34, 0.85);
      color: var(--text-primary);
      font-size: 0.95rem;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }
    .summary-card {
      background: var(--surface-strong);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 1.2rem 1.4rem;
      transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .summary-card:hover {
      box-shadow: 0 0 30px var(--glow);
      transform: translateY(-2px);
    }
    .summary-card h3 {
      margin: 0 0 0.4rem;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--text-muted);
      font-weight: 600;
    }
    .summary-card strong {
      font-size: 1.9rem;
      font-weight: 700;
    }
    .actions {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-top: 1rem;
    }
    .button-secondary {
      background: rgba(19, 24, 46, 0.9);
      border: 1px solid var(--border);
      color: var(--text-primary);
      padding: 0.55rem 1.2rem;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 600;
      font-size: 0.95rem;
      box-shadow: 0 12px 24px rgba(7, 12, 30, 0.35);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1.25rem;
      font-size: 0.95rem;
    }
    th, td {
      text-align: left;
      padding: 0.8rem 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    th {
      color: var(--text-muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }
    tbody tr {
      transition: background 0.2s ease;
    }
    tbody tr:hover {
      background: rgba(92, 124, 255, 0.08);
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      padding: 0.25rem 0.7rem;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    .status-ready {
      background: rgba(45, 212, 167, 0.18);
      color: var(--success);
      border: 1px solid rgba(45, 212, 167, 0.35);
    }
    .status-review {
      background: rgba(243, 181, 68, 0.18);
      color: var(--warning);
      border: 1px solid rgba(243, 181, 68, 0.35);
    }
    .muted {
      color: var(--text-muted);
      font-size: 0.95rem;
    }
    @media (max-width: 720px) {
      body {
        padding: 1.5rem 1rem 3rem;
      }
      nav {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.75rem;
      }
      .nav-links {
        flex-wrap: wrap;
      }
      .actions {
        flex-direction: column;
        align-items: stretch;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <nav>
      <div class="logo">speer</div>
      <div class="nav-links">
        <a href="#dashboard">Dashboard</a>
        <a href="#exports">Exports</a>
        <form action="/upload" method="post" enctype="multipart/form-data">
          <label for="nav-upload" class="button-primary">Upload</label>
          <input id="nav-upload" name="files" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.xml" hidden />
        </form>
      </div>
    </nav>

    <section class="hero" id="dashboard">
      <div>
        <h1>Invoice evidence, prepared for safe payments.</h1>
        <p>Speer keeps every file as evidence, extracts payment details, and flags anything that needs manual review.</p>
        <div class="notice">
          Payments are never executed automatically. Always review and approve in your bank system.
        </div>
      </div>
      <div class="panel upload-box">
        <div>
          <strong>Upload evidence files</strong>
          <p class="muted">Accepted: PDF, PNG, JPG, JPEG, XML</p>
        </div>
        <form action="/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="files" multiple accept=".pdf,.png,.jpg,.jpeg,.xml" />
          <button class="button-primary" type="submit">Upload evidence</button>
        </form>
      </div>
    </section>

    <section class="summary">
      <div class="summary-card">
        <h3>Total processed</h3>
        <strong id="total-count">0</strong>
      </div>
      <div class="summary-card">
        <h3>Ready for payment</h3>
        <strong id="ready-count">0</strong>
      </div>
      <div class="summary-card">
        <h3>Needs review</h3>
        <strong id="review-count">0</strong>
      </div>
    </section>

    <section class="panel" id="exports">
      <h2>Latest evidence</h2>
      <table>
        <thead>
          <tr>
            <th>File name</th>
            <th>Status</th>
            <th>Amount</th>
            <th>IBAN</th>
            <th>Reference</th>
          </tr>
        </thead>
        <tbody id="invoice-table">
          <tr><td colspan="5">No evidence uploaded yet.</td></tr>
        </tbody>
      </table>
      <div class="actions">
        <a class="button-secondary" href="/download/all">Download all invoices</a>
        <a class="button-secondary" href="/download/payments">Download payment instructions</a>
        <a class="button-secondary" href="/download/review">Download review file</a>
      </div>
    </section>
  </div>

  <script>
    const tableBody = document.getElementById("invoice-table");
    const totalCount = document.getElementById("total-count");
    const readyCount = document.getElementById("ready-count");
    const reviewCount = document.getElementById("review-count");

    function formatAmount(value) {
      if (value === null || value === undefined) {
        return "-";
      }
      return Number(value).toFixed(2);
    }

    function renderRows(records) {
      if (!records.length) {
        tableBody.innerHTML = '<tr><td colspan="5">No evidence uploaded yet.</td></tr>';
        return;
      }

      const rows = records.map((record) => {
        const statusLabel = record.payment_ready ? "Ready" : "Review";
        const statusClass = record.payment_ready ? "status-ready" : "status-review";
        const reference = record.invoice_number || record.file_name || "UNKNOWN";
        return `
          <tr>
            <td>${record.file_name || "-"}</td>
            <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
            <td>${formatAmount(record.total_amount)}</td>
            <td>${record.iban || "-"}</td>
            <td>${reference}</td>
          </tr>
        `;
      });
      tableBody.innerHTML = rows.join("");
    }

    function updateSummary(records) {
      const total = records.length;
      const ready = records.filter((record) => record.payment_ready).length;
      const review = total - ready;
      totalCount.textContent = total;
      readyCount.textContent = ready;
      reviewCount.textContent = review;
    }

    async function fetchInvoices() {
      try {
        const response = await fetch("/api/invoices");
        if (!response.ok) {
          return;
        }
        const records = await response.json();
        updateSummary(records);
        renderRows(records);
      } catch (error) {
        console.error("Failed to load invoices", error);
      }
    }

    fetchInvoices();
  </script>
</body>
</html>
"""


def _safe_filename(filename: str | None) -> str:
    if not filename:
        return "evidence"
    return Path(filename).name


def _hash_bytes(content: bytes) -> str:
    hasher = sha256()
    hasher.update(content)
    return hasher.hexdigest()


def _write_upload(content: bytes, filename: str) -> Path:
    unique_name = f"{uuid4().hex}_{filename}"
    target_path = UPLOAD_DIR / unique_name
    target_path.write_bytes(content)
    return target_path


def _export_paths(run_id: str) -> dict:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return {
        "xlsx": EXPORT_DIR / f"speer_{run_id}_{timestamp}.xlsx",
        "json": EXPORT_DIR / f"speer_{run_id}_{timestamp}.json",
        "ok_xlsx": EXPORT_DIR / f"speer_{run_id}_{timestamp}_payment.xlsx",
        "review_xlsx": EXPORT_DIR / f"speer_{run_id}_{timestamp}_review.xlsx",
        "review_json": EXPORT_DIR / f"speer_{run_id}_{timestamp}_review.json",
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_PAGE


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)) -> RedirectResponse:
    global latest_records, latest_exports

    run_id = uuid4().hex[:10]
    upload_paths: list[Path] = []

    for upload in files:
        safe_name = _safe_filename(upload.filename)
        suffix = Path(safe_name).suffix.lower()

        if suffix and suffix not in ALLOWED_SUFFIXES:
            suffix = suffix

        content = await upload.read()
        _hash_bytes(content)
        file_path = _write_upload(content, safe_name)
        upload_paths.append(file_path)

    export_paths = _export_paths(run_id)
    latest_records = speer_core.process_evidence_files(
        upload_paths,
        export_paths["xlsx"],
        export_paths["json"],
        export_paths["ok_xlsx"],
        export_paths["review_xlsx"],
        export_paths["review_json"],
        run_id,
    )
    latest_exports = {key: str(path) for key, path in export_paths.items()}

    return RedirectResponse(url="/", status_code=303)


@app.get("/api/invoices")
def api_invoices() -> JSONResponse:
    payload = [
        {
            "file_name": record.get("file_name"),
            "status": record.get("status"),
            "payment_ready": record.get("payment_ready"),
            "total_amount": record.get("total_amount"),
            "iban": record.get("iban"),
            "invoice_number": record.get("invoice_number"),
        }
        for record in latest_records
    ]
    return JSONResponse(payload)


@app.get("/download/all")
def download_all() -> FileResponse:
    if not latest_exports or not latest_exports.get("xlsx"):
        return HTMLResponse(
            "No export available yet. Upload evidence files first.", status_code=404
        )
    return FileResponse(latest_exports["xlsx"], filename="speer_invoices.xlsx")


@app.get("/download/payments")
def download_payments() -> FileResponse:
    if not latest_exports or not latest_exports.get("ok_xlsx"):
        return HTMLResponse(
            "No payment file available yet. Upload evidence files first.",
            status_code=404,
        )
    return FileResponse(latest_exports["ok_xlsx"], filename="speer_payments.xlsx")


@app.get("/download/review")
def download_review() -> FileResponse:
    if not latest_exports or not latest_exports.get("review_xlsx"):
        return HTMLResponse(
            "No review file available yet. Upload evidence files first.",
            status_code=404,
        )
    return FileResponse(latest_exports["review_xlsx"], filename="speer_review.xlsx")
