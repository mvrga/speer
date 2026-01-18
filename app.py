from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

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

latest_exports: dict | None = None


HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Speer</title>
  <style>
    :root {
      color-scheme: light;
      font-family: "Source Serif 4", "Iowan Old Style", "Times New Roman", serif;
      background: radial-gradient(circle at top, #f7f2ea 0%, #efe6d8 50%, #e8dcc9 100%);
      color: #2f2a24;
    }
    body {
      margin: 0;
      padding: 2rem 1.25rem 3rem;
    }
    .wrap {
      max-width: 760px;
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
      margin: 0 0 1.5rem;
      font-size: 1.05rem;
      line-height: 1.5;
    }
    .card {
      border: 1px dashed #bda98e;
      padding: 1.5rem;
      border-radius: 12px;
      background: #fffaf2;
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
    .links {
      margin-top: 1.5rem;
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }
    a {
      color: #6c4f2e;
      text-decoration: none;
      font-weight: 600;
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
    <h1>Speer</h1>
    <p>Evidence-first invoice ingestion. Every file is recorded and never discarded.</p>
    <div class="card">
      <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="files" multiple accept=".pdf,.png,.jpg,.jpeg,.xml,.zip" />
        <button type="submit">Upload evidence</button>
      </form>
    </div>
    <div class="links">
      <a href="/export">Latest export</a>
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
    return speer_core.EvidenceRecord(
        file_path=str(data.get("file_path", "")),
        sha256=str(data.get("sha256", "")),
        invoice_number=data.get("invoice_number"),
        invoice_date=data.get("invoice_date"),
        total_amount=data.get("total_amount"),
        currency=data.get("currency"),
        iban=data.get("iban"),
        bic=data.get("bic"),
        status=str(data.get("status", "needs_review")),
        parse_errors=list(data.get("parse_errors", [])),
    )


def _process_pdf(file_path: Path) -> speer_core.EvidenceRecord:
    if hasattr(speer_core, "process_invoice"):
        result = speer_core.process_invoice(file_path)
        if isinstance(result, dict):
            return _record_from_dict(result)
        return result
    return speer_core.parse_invoice_pdf(file_path)


def _merge_errors(
    record: speer_core.EvidenceRecord, errors: Iterable[str]
) -> speer_core.EvidenceRecord:
    errors_list = list(errors)
    if not errors_list:
        return record
    return replace(
        record,
        status="needs_review",
        parse_errors=record.parse_errors + errors_list,
    )


def _non_pdf_record(
    file_path: str, file_hash: str, suffix: str, errors: Iterable[str], reason: str
) -> speer_core.EvidenceRecord:
    parse_errors = list(errors)
    parse_errors.append(reason)
    return speer_core.EvidenceRecord(
        file_path=file_path,
        sha256=file_hash,
        invoice_number=None,
        invoice_date=None,
        total_amount=None,
        currency=None,
        iban=None,
        bic=None,
        status="needs_review",
        parse_errors=parse_errors,
    )


def _export_outputs(records: list[speer_core.EvidenceRecord], run_id: str) -> dict:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    xlsx_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}.xlsx"
    json_path = EXPORT_DIR / f"speer_{run_id}_{timestamp}.json"

    if hasattr(speer_core, "export_outputs"):
        return speer_core.export_outputs(records, xlsx_path, json_path)

    speer_core.export_xlsx(records, xlsx_path)
    speer_core.export_json_audit(records, json_path)

    return {
        "xlsx": str(xlsx_path),
        "json": str(json_path),
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_PAGE


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)) -> JSONResponse:
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
                suffix=suffix,
                errors=[f"upload_read_error:{exc}"],
                reason=f"unsupported_format:{suffix or 'unknown'}",
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
            record = _process_pdf(file_path)
            record = _merge_errors(record, errors)
            records.append(record)
            continue
        if suffix == ".pdf" and file_path is None:
            record = speer_core.EvidenceRecord(
                file_path=f"memory:{safe_name}",
                sha256=file_hash,
                invoice_number=None,
                invoice_date=None,
                total_amount=None,
                currency=None,
                iban=None,
                bic=None,
                status="needs_review",
                parse_errors=errors + ["pdf_unavailable"],
            )
            records.append(record)
            continue

        file_location = str(file_path) if file_path else f"memory:{safe_name}"
        reason = (
            f"non_pdf_evidence:{suffix or 'unknown'}"
            if is_allowed
            else f"unsupported_format:{suffix or 'unknown'}"
        )
        record = _non_pdf_record(file_location, file_hash, suffix, errors, reason)
        records.append(record)

    export_info = _export_outputs(records, run_id)
    global latest_exports
    latest_exports = export_info

    payload = {
        "run_id": run_id,
        "processed": len(records),
        "ok": sum(1 for record in records if record.status == "ok"),
        "needs_review": sum(
            1 for record in records if record.status == "needs_review"
        ),
        "records": [record.to_dict() for record in records],
        "exports": export_info,
    }

    return JSONResponse(payload)


@app.get("/export")
def export() -> JSONResponse:
    if not latest_exports:
        return JSONResponse(
            {"message": "No exports generated yet.", "exports": None}, status_code=200
        )
    return JSONResponse(
        {
            "message": "Exports generated.",
            "exports": latest_exports,
        }
    )
