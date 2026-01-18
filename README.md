# Speer

Speer is an invoice evidence ingestion system. It extracts payment‑critical fields from PDFs and records every submitted file, even when parsing fails.

## Why evidence
Invoices are treated as financial evidence. Each file is stored, hashed, and included in the audit log so that processing decisions can be reviewed later.

## Supported formats
- PDF (parsed)
- PNG, JPG/JPEG, XML, ZIP (registered as evidence, marked for review)

## Auditability
Each run produces a JSON audit log with run ID, timestamp, and SHA256 hashes for all files. Parsing errors are recorded explicitly; nothing is discarded silently.

## Local run (macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` and upload evidence files.

## Outputs
- XLSX report with extracted fields and status
- JSON audit log with run metadata and file hashes

## Limitations
- No OCR in the MVP; image‑only PDFs or images are not parsed and require review.
