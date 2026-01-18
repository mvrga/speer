import hashlib
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from pypdf import PdfReader
from openpyxl import Workbook


# =========================
# Regex patterns (DE + EN)
# =========================

IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
BIC_PATTERN = re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b")

INVOICE_NUMBER_PATTERNS = [
    r"Rechnungsnummer\s*[:#]?\s*([A-Z0-9\-\/]+)",
    r"Invoice\s*Number\s*[:#]?\s*([A-Z0-9\-\/]+)",
    r"\bRE\s*[:#]?\s*(\d+)",
]

AMOUNT_PATTERNS = [
    r"(Gesamtbetrag|Rechnungsbetrag|Insgesamt|Total)\s*([0-9\.,]+)\s*(EUR|€)"
]

DATE_PATTERN = r"(\d{2}\.\d{2}\.\d{4})"


# =========================
# Utilities
# =========================

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(data)
    text_parts: List[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def find_first(patterns: List[str], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def normalize_amount(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    value = raw.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


# =========================
# Core processing
# =========================

def process_invoice(file_path: str, run_id: str) -> Dict:
    with open(file_path, "rb") as handle:
        content = handle.read()

    text = extract_text_from_pdf(content)

    invoice_number = find_first(INVOICE_NUMBER_PATTERNS, text)

    date_match = re.search(DATE_PATTERN, text)
    invoice_date = date_match.group(1) if date_match else None

    amount_raw = None
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_raw = match.group(2)
            break

    amount_value = normalize_amount(amount_raw)

    iban_match = IBAN_PATTERN.search(text.replace(" ", ""))
    iban = iban_match.group(0) if iban_match else None

    bic_match = BIC_PATTERN.search(text.replace(" ", ""))
    bic = bic_match.group(0) if bic_match else None

    errors: List[str] = []
    if not invoice_number:
        errors.append("Missing invoice number")
    if not amount_value or amount_value <= 0:
        errors.append("Invalid amount")
    if not iban:
        errors.append("Missing IBAN")

    status = "ok" if not errors else "needs_review"

    return {
        "run_id": run_id,
        "source_file": os.path.basename(file_path),
        "file_sha256": sha256_hex(content),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "amount": amount_value,
        "currency": "EUR",
        "iban": iban,
        "bic": bic,
        "status": status,
        "errors": errors,
    }


def export_outputs(records: List[Dict], output_dir: str, run_id: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Invoices"

    headers = list(records[0].keys())
    sheet.append(headers)

    for record in records:
        sheet.append([str(record[h]) for h in headers])

    workbook.save(os.path.join(output_dir, f"invoices-{run_id}.xlsx"))

    audit_payload = {
        "run_id": run_id,
        "timestamp_utc": datetime.utcnow().isoformat(),
        "records": records,
    }

    with open(os.path.join(output_dir, f"audit-{run_id}.json"), "w", encoding="utf-8") as handle:
        json.dump(audit_payload, handle, indent=2)

