# Speer

## Overview
Speer is a financial evidence ingestion system. It reads invoices, extracts payment‑critical fields, and stores every file as evidence. The system is deterministic and audit‑oriented: every decision is traceable and every file remains available for review.

## Architecture
Speer achieves near‑100% coverage through layered extraction:
- XML when available (highest reliability)
- PDF text extraction for digital invoices
- OCR fallback for scanned PDFs and images
- Manual review for edge cases and ambiguous data

This layered approach avoids guessing. If a field is missing or uncertain, Speer marks the record for review instead of assuming values.

## Dashboard
The dashboard is a single‑page HTML interface for business managers. It shows:
- Total evidence uploaded
- Invoices ready for payment
- Invoices needing review
- A simple table with file name, status, payment readiness, and amount

Uploads are accepted in PDF, PNG, JPG/JPEG, XML, and ZIP. Every upload is recorded as evidence, even if parsing fails.

## Payments & Revolut
Speer prepares payment instruction files but does not execute payments. This keeps approval separate from extraction and reduces operational risk. The payment file format is compatible with Revolut Business batch payment imports, so finance teams can review and submit payments in their banking interface.

## Review workflow
When a record is marked as needs_review, Speer generates a review pack:
- A manager‑friendly XLSX with key fields and errors
- A developer‑focused JSON log for troubleshooting

This ensures operational clarity for both finance and technical teams.

## How to run locally (macOS M1)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/dashboard`.

## Limitations & roadmap
- No automated payment execution; payments always require manual approval.
- OCR quality depends on scan quality and the local Tesseract install.
- XML parsing is a stub in the MVP; planned next step is full support for structured e‑invoice formats.
