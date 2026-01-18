from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

import speer_core


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
EXPORT_DIR = OUTPUT_DIR / "exports"

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".xml", ".zip"}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Speer")

latest_records: list[speer_core.EvidenceRecord] = []
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
      color-scheme: light;
      font-family: "Source Serif 4", "Iowan Old Style", "Times New Roman", serif;
      background: linear-gradient(180deg, #f8f3ea 0%, #efe4d3 60%, #e6dac6 100%);
      color: #2f2a24;
    }
    body {
      margin: 0;
      padding: 2rem 1.25rem 3rem;
    }
    .wrap {
      max-width: 980px;
      margin: 0 auto;
      background: #fdfbf6;
      border: 1px solid #e1d6c5;
      border-radius: 16px;
      padding: 2rem;
      box-shadow: 0 18px 36px rgba(56, 46, 36, 0.08);
    }
    h1 {
      margin: 0 0 0.5rem;
      font-size: clamp(2rem, 4vw, 2.8rem);
      letter-spacing: 0.02em;
    }
    p {
      margin: 0 0 1.25rem;
      font-size: 1.05rem;
      line-height: 1.5;
    }
    .panel {
      border: 1px solid #d8c6aa;
      border-radius: 12px;
      padding: 1.5rem;
      background: #fffaf2;
      margin-bottom: 1.5rem;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .summary-card {
      background: #fff;
      border: 1px solid #e1d6c5;
      border-radius: 12px;
      padding: 1rem 1.25rem;
    }
    .summary-card h3 {
      margin: 0 0 0.35rem;
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #6b5a46;
    }
    .summary-card strong {
      font-size: 1.6rem;
    }
    input[type="file"] {
      width: 100%;
      padding: 0.75rem;
      border-radius: 10px;
      border: 1px solid #c9b69c;
      background: #fff;
      font-size: 1rem;
    }
    button {
      margin-top: 1rem;
      background: #6c4f2e;
      color: #fff;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 999px;
      font-size: 1rem;
      cursor: pointer;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      font-size: 0.98rem;
    }
    th, td {
      text-align: left;
      padding: 0.6rem 0.4rem;
      border-bottom: 1px solid #e1d6c5;
    }
    th {
      color: #6b5a46;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .status-ok {
      color: #2f6b2f;
      font-weight: 600;
    }
    .status-review {
      color: #9c4a2e;
      font-weight: 600;
    }
    .actions {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      margin-top: 1rem;
    }
    .actions a {
      background: #f0e4d2;
      border: 1px solid #d4c0a3;
      padding: 0.6rem 1rem;
      border-radius: 999px;
      color: #4f3b25;
      text-decoration: none;
      font-weight: 600;
    }
    .notice {
      border-left: 4px solid #9c4a2e;
      padding: 0.75rem 1rem;
      background: #fff5ec;
      color: #5a3220;
      margin-bottom: 1.5rem;
    }
    .muted {
      color: #6b5a46;
      font-size: 0.95rem;
    }
    @media (max-width: 640px) {
      body {
        padding: 1.5rem 1rem 2rem;
      }
      .wrap {
        padding: 1.5rem;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Speer Dashboard</h1>
    <p>Every file is stored as financial evidence. If Speer is unsure, it marks the file for review.</p>

    <div class="notice">
      Payments are never executed automatically. Always review and approve before sending any payment file.
    </div>

    <div class="panel">
      <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="files" multiple accept=".pdf,.png,.jpg,.jpeg,.xml,.zip" />
        <button type="submit">Upload evidence files</button>
      </form>
      <p class="muted">Accepted: PDF, PNG, JPG, JPEG, XML, ZIP</p>
    </div>

    <div class="summary">
      <div class="summary-card">
        <h3>Total uploaded</h3>
        <strong>{{total_count}}</strong>
      </div>
      <div class="summary-card">
        <h3>Ready for payment</h3>
        <strong>{{ok_count}}</strong>
      </div>
      <div class="summary-card">
        <h3>Needs review</h3>
        <strong>{{review_count}}</strong>
      </div>
    </div>

    <div class="panel">
      <h2>Latest evidence</h2>
      <table>
        <thead>
          <tr>
            <th>File name</th>
            <th>Status</th>
            <th>Payment ready</th>
            <th>Amount (EUR)</th>
          </tr>
        </thead>
        <tbody>
          {{table_rows}}
        </tbody>
      </table>
      <div class="actions">
        <a href="/download/all">Download Excel (all invoices)</a>
        <a href="/download/ok">Download payment file</a>
        <a href="/download/review">Download review file</a>
      </div>
    </div>
  </div>
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


def _record_from_dict(data: dict) -> speer_core.EvidenceRecord:
    file_path = str(data.get("file_path", ""))
    file_name = data.get("file_name") or Path(file_path).name
    return speer_core.EvidenceRecord(
        file_path=file_path,
        file_name=file_name,
        sha256=str(data.get("sha256", "")),
        evidence_type=str(data.get("evidence_type", "unknown")),
        extraction_method=str(data.get("extraction_method", "unknown")),
        text_preview=str(data.get("text_preview", "")),
        invoice_number=data.get("invoice_number"),
        invoice_date=data.get("invoice_date"),
        total_amount=data.get("total_amount"),
        currency=data.get("currency"),
        iban=data.get("iban"),
        bic=data.get("bic"),
        status=str(data.get("status", "needs_review")),
        payment_ready=bool(data.get("payment_ready")),
        parse_errors=list(data.get("parse_errors", [])),
    )


def _non_pdf_record(
    file_path: str, file_hash: str, reason: str, errors: Iterable[str]
) -> speer_core.EvidenceRecord:
    parse_errors = list(errors)
    parse_errors.append(reason)
    return speer_core.EvidenceRecord(
        file_path=file_path,
        file_name=Path(file_path).name,
        sha256=file_hash,
        evidence_type="unknown",
        extraction_method="unknown",
        text_preview="",
        invoice_number=None,
        invoice_date=None,
        total_amount=None,
        currency=None,
        iban=None,
        bic=None,
        status="needs_review",
        payment_ready=False,
        parse_errors=parse_errors,
    )


def _render_dashboard(records: list[speer_core.EvidenceRecord]) -> str:
    total_count = len(records)
    ok_count = sum(1 for record in records if record.payment_ready)
    review_count = total_count - ok_count

    if records:
        rows = []
        for record in records:
            amount = (
                f"{record.total_amount:.2f}" if record.total_amount is not None else "-"
            )
            status_class = "status-ok" if record.status == "ok" else "status-review"
            payment_ready = "Yes" if record.payment_ready else "No"
            rows.append(
                "<tr>"
                f"<td>{record.file_name}</td>"
                f"<td class=\"{status_class}\">{record.status.replace('_', ' ')}</td>"
                f"<td>{payment_ready}</td>"
                f"<td>{amount}</td>"
                "</tr>"
            )
        table_rows = "\n".join(rows)
    else:
        table_rows = (
            "<tr><td colspan=\"4\">No evidence uploaded yet.</td></tr>"
        )

    return (
        HTML_PAGE.replace("{{total_count}}", str(total_count))
        .replace("{{ok_count}}", str(ok_count))
        .replace("{{review_count}}", str(review_count))
        .replace("{{table_rows}}", table_rows)
    )


def _export_outputs(records: list[speer_core.EvidenceRecord], run_id: str) -> dict:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    xlsx_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}.xlsx"
    json_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}.json"
    ok_xlsx_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}_payment.xlsx"
    review_xlsx_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}_review.xlsx"
    review_json_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}_review.json"

    if hasattr(speer_core, "export_outputs"):
        return speer_core.export_outputs(
            records,
            xlsx_path,
            json_path,
            ok_xlsx_path,
            review_xlsx_path,
            review_json_path,
            run_id,
        )

    speer_core.export_xlsx(records, xlsx_path)
    speer_core.export_payment_instructions(records, ok_xlsx_path)
    speer_core.export_review_pack(records, review_xlsx_path)
    speer_core.export_json_audit(records, json_path, run_id)
    speer_core.export_review_json(records, review_json_path, run_id)

    return {
        "run_id": run_id,
        "xlsx": str(xlsx_path),
        "json": str(json_path),
        "ok_xlsx": str(ok_xlsx_path),
        "review_xlsx": str(review_xlsx_path),
        "review_json": str(review_json_path),
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _render_dashboard(latest_records)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return _render_dashboard(latest_records)


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)) -> RedirectResponse:
    global latest_records, latest_exports

    run_id = uuid4().hex[:10]
    records: list[speer_core.EvidenceRecord] = []

    for upload in files:
        safe_name = _safe_filename(upload.filename)
        suffix = Path(safe_name).suffix.lower()
        is_allowed = suffix in ALLOWED_SUFFIXES

        errors: list[str] = []
        try:
            content = await upload.read()
        except Exception as exc:  # noqa: BLE001 - evidence capture should never fail silently
            record = _non_pdf_record(
                file_path=f"memory:{safe_name}",
                file_hash="",
                reason=f"unsupported_format:{suffix or 'unknown'}",
                errors=[f"upload_read_error:{exc}"],
            )
            records.append(record)
            continue

        file_hash = _hash_bytes(content)
        file_path: Path | None = None
        try:
            file_path = _write_upload(content, safe_name)
        except Exception as exc:  # noqa: BLE001 - evidence capture should never fail silently
            errors.append(f"file_write_error:{exc}")

        if suffix == ".pdf" and file_path is not None:
            result = speer_core.process_invoice(file_path)
            record = _record_from_dict(result)
            if errors:
                record = _record_from_dict(
                    {
                        **record.to_dict(),
                        "status": "needs_review",
                        "payment_ready": False,
                        "parse_errors": record.parse_errors + errors,
                    }
                )
            records.append(record)
            continue

        if not is_allowed:
            reason = f"unsupported_format:{suffix or 'unknown'}"
        else:
            reason = f"non_pdf_evidence:{suffix or 'unknown'}"

        file_location = str(file_path) if file_path else f"memory:{safe_name}"
        record = _non_pdf_record(file_location, file_hash, reason, errors)
        records.append(record)

    latest_records = records
    latest_exports = _export_outputs(records, run_id)

    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/download/all")
def download_all() -> FileResponse:
    if not latest_exports or not latest_exports.get("xlsx"):
        return HTMLResponse(
            "No export available yet. Upload evidence files first.", status_code=404
        )
    return FileResponse(latest_exports["xlsx"], filename="speer_invoices.xlsx")


@app.get("/download/ok")
def download_ok() -> FileResponse:
    if not latest_exports or not latest_exports.get("ok_xlsx"):
        return HTMLResponse(
            "No payment file available yet. Upload evidence files first.",
            status_code=404,
        )
    return FileResponse(latest_exports["ok_xlsx"], filename="speer_payment.xlsx")


@app.get("/download/review")
def download_review() -> FileResponse:
    if not latest_exports or not latest_exports.get("review_xlsx"):
        return HTMLResponse(
            "No review file available yet. Upload evidence files first.",
            status_code=404,
        )
    return FileResponse(latest_exports["review_xlsx"], filename="speer_review.xlsx")
