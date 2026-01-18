# Testing

Manual testing focused on auditability and payment safety. Evidence is never discarded, and the system degrades safely when extraction fails.

## Coverage
- Batch upload of real invoices through the dashboard
- PDF text invoices parsed via pypdf extraction
- Scanned invoices parsed via OCR fallback
- Unsupported evidence formats (e.g., ZIP/XML) recorded as needs_review
- Review workflow using the review XLSX and review JSON outputs
- Payment file generation for payment‑ready invoices

## Notes
- Each upload batch produced a new run ID and export set.
- Failures were recorded in parse errors rather than hidden.
- Payment files were generated only when required fields were present.
