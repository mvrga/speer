# Testing

Manual testing focused on payment safety and auditability. Evidence is never discarded; the system degrades safely when parsing fails.

## Test cases
1) Valid PDF invoice
- Upload a PDF with a clear invoice number, IBAN, and total amount.
- Expect status = ok and fields populated in the evidence XLSX and JSON audit log.

2) Unsupported evidence format
- Upload a file such as `.zip` or `.xml`.
- Expect a record created with status = needs_review and a parse error noting the format.

3) PDF without extractable text
- Upload a scanned PDF (image-only).
- Expect a record created with status = needs_review and a parse error indicating PDF read/text extraction issues.

4) Multiple uploads generate different run IDs
- Upload two separate batches.
- Expect different `run_id` values in each JSON audit log and distinct export filenames.

5) Audit log verification
- Confirm each record in the JSON audit log includes `file_path` and `sha256`.
- Verify that each uploaded file appears exactly once and that failed parses are still recorded.

## Notes
- The system keeps all evidence and marks uncertain cases for review.
- Parsing failures never block export generation.
