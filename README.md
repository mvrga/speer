# Speer

## Overview
Speer is a financial evidence ingestion system for invoices. It extracts payment‑critical fields, stores every file as evidence, and prepares payment files for manual approval.

## Key concepts
- Invoices are treated as evidence: every file is stored and logged, even when parsing fails.
- Extraction uses PDF text parsing with OCR fallback for scans.
- Payment preparation is separated from payment execution.

## Features
- Upload PDFs, images, XML, and ZIP files.
- Automatic extraction of invoice number, date, amount, currency, IBAN, and BIC.
- Audit log with SHA256 hashes and run metadata.
- Exports:
  - XLSX for all invoices
  - XLSX payment instruction file (payment‑ready only)
  - XLSX review file (needs_review only)
  - JSON audit log and review log

## Local setup (macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local setup (Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local setup (Windows)
```powershell
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## Run the app
```bash
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/dashboard`.

## Local test quick-check (Linux/Windows/macOS)
- Start the app and upload at least one PDF.
- Confirm the dashboard counters update and the download buttons return files.

## Manual testing steps
1) Upload a valid PDF invoice with clear invoice number, IBAN, and amount.
2) Upload a scanned invoice (image‑only PDF) to trigger OCR fallback.
3) Upload an unsupported file (e.g., ZIP) to verify it is recorded as needs_review.
4) Upload a second batch to confirm a new run ID and new export files.
5) Download the exports and verify:
   - Payment file contains only payment‑ready invoices.
   - Review file contains all needs_review invoices.
   - JSON audit log contains SHA256 hashes and all records.

## Notes
- Payments are never executed automatically; approvals happen outside Speer.
- If extraction is uncertain, records are flagged for review.
