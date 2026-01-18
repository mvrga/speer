import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from pypdf import PdfReader


@dataclass(frozen=True)
class EvidenceRecord:
    file_path: str
    file_name: str
    sha256: str
    invoice_number: str | None
    invoice_date: str | None
    total_amount: float | None
    currency: str
    iban: str | None
    bic: str | None
    beneficiary_name: str | None
    status: str
    parse_errors: list[str]

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "sha256": self.sha256,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "iban": self.iban,
            "bic": self.bic,
            "beneficiary_name": self.beneficiary_name,
            "status": self.status,
            "parse_errors": self.parse_errors,
        }


def _file_sha256(file_path: Path) -> str:
    hasher = sha256()
    with file_path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _extract_text_from_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages_text: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages_text.append(page_text)
    return "\n".join(pages_text)


def _first_match(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def _normalize_amount(raw_amount: str) -> float | None:
    cleaned = raw_amount.strip()
    cleaned = cleaned.replace("\u00a0", "").replace(" ", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _amount_from_filename(file_name: str) -> float | None:
    amount_pattern = re.compile(
        r"([0-9]{1,3}(?:[._][0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:,[0-9]{2})?)"
    )
    match = amount_pattern.search(file_name)
    if not match:
        return None
    return _normalize_amount(match.group(1))


def _parse_invoice_text(file_path: Path, text: str) -> EvidenceRecord:
    parse_errors: list[str] = []

    invoice_number_pattern = re.compile(
        r"(?:invoice\s*number|invoice\s*no\.?|inv\.\s*no\.?|facture\s*no\.?|rechnung\s*nr\.?)\s*[:#]?\s*([A-Z0-9\-/]+)",
        re.IGNORECASE,
    )
    invoice_date_pattern = re.compile(
        r"(?:invoice\s*date|date)\s*[:#]?\s*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2}|[0-9]{2}[-/][0-9]{2}[-/][0-9]{4})",
        re.IGNORECASE,
    )
    total_amount_pattern = re.compile(
        r"(?:total\s*amount|amount\s*due|total)\s*[:#]?\s*([0-9][0-9\s.,]*)",
        re.IGNORECASE,
    )
    currency_pattern = re.compile(r"\b(EUR|€)\b", re.IGNORECASE)
    iban_pattern = re.compile(r"\b([A-Z]{2}[0-9A-Z]{13,30})\b")
    bic_pattern = re.compile(r"\b([A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?)\b")

    invoice_number = _first_match(invoice_number_pattern, text)
    invoice_date = _first_match(invoice_date_pattern, text)
    raw_amount = _first_match(total_amount_pattern, text)

    currency = "EUR"
    if not currency_pattern.search(text):
        parse_errors.append("currency_missing")

    iban = _first_match(iban_pattern, text)
    bic = _first_match(bic_pattern, text)

    total_amount = None
    if raw_amount:
        total_amount = _normalize_amount(raw_amount)
        if total_amount is None:
            parse_errors.append("total_amount_invalid")
    else:
        total_amount = _amount_from_filename(file_path.name)
        if total_amount is None:
            parse_errors.append("total_amount_missing")
        else:
            parse_errors.append("total_amount_from_filename")

    if invoice_number is None:
        parse_errors.append("invoice_number_missing")

    if invoice_date is None:
        parse_errors.append("invoice_date_missing")

    if iban is None:
        parse_errors.append("iban_missing")

    if total_amount is not None and total_amount <= 0:
        parse_errors.append("total_amount_non_positive")

    status = "ok"
    if invoice_number is None or iban is None or total_amount is None or total_amount <= 0:
        status = "needs_review"

    return EvidenceRecord(
        file_path=str(file_path),
        file_name=file_path.name,
        sha256=_file_sha256(file_path),
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        total_amount=total_amount,
        currency=currency,
        iban=iban,
        bic=bic,
        beneficiary_name=None,
        status=status,
        parse_errors=parse_errors,
    )


def parse_invoice_pdf(file_path: Path) -> EvidenceRecord:
    try:
        text = _extract_text_from_pdf(file_path)
    except Exception as exc:  # noqa: BLE001
        return EvidenceRecord(
            file_path=str(file_path),
            file_name=file_path.name,
            sha256=_file_sha256(file_path),
            invoice_number=None,
            invoice_date=None,
            total_amount=None,
            currency="EUR",
            iban=None,
            bic=None,
            beneficiary_name=None,
            status="needs_review",
            parse_errors=[f"pdf_read_error:{exc}"],
        )

    return _parse_invoice_text(file_path, text)


def process_invoice(file_path: str | Path) -> dict:
    record = parse_invoice_pdf(Path(file_path))
    return record.to_dict()


def parse_invoice_files(file_paths: Iterable[Path]) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for file_path in file_paths:
        records.append(parse_invoice_pdf(file_path))
    return records


def export_xlsx(records: Iterable[EvidenceRecord], output_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "speer_evidence"

    headers = [
        "file_path",
        "file_name",
        "sha256",
        "invoice_number",
        "invoice_date",
        "total_amount",
        "currency",
        "iban",
        "bic",
        "beneficiary_name",
        "status",
        "parse_errors",
    ]
    worksheet.append(headers)

    for record in records:
        worksheet.append(
            [
                record.file_path,
                record.file_name,
                record.sha256,
                record.invoice_number,
                record.invoice_date,
                record.total_amount,
                record.currency,
                record.iban,
                record.bic,
                record.beneficiary_name,
                record.status,
                ";".join(record.parse_errors),
            ]
        )

    workbook.save(output_path)


def export_payment_instructions(records: Iterable[EvidenceRecord], output_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "payment_instructions"

    headers = [
        "beneficiary_name",
        "iban",
        "bic",
        "amount",
        "currency",
        "reference",
    ]
    worksheet.append(headers)

    for record in records:
        if record.status != "ok":
            continue
        worksheet.append(
            [
                record.beneficiary_name,
                record.iban,
                record.bic,
                record.total_amount,
                record.currency,
                record.invoice_number,
            ]
        )

    workbook.save(output_path)


def export_json_audit(records: Iterable[EvidenceRecord], output_path: Path, run_id: str) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "run_id": run_id,
        "timestamp": timestamp,
        "records": [record.to_dict() for record in records],
    }

    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)

    return payload


def export_outputs(
    records: Iterable[EvidenceRecord],
    xlsx_output_path: str | Path,
    json_output_path: str | Path,
    ok_xlsx_output_path: str | Path | None = None,
    run_id: str | None = None,
) -> dict:
    resolved_run_id = run_id or str(uuid.uuid4())
    export_xlsx(records, Path(xlsx_output_path))
    export_json_audit(records, Path(json_output_path), resolved_run_id)

    ok_output = None
    if ok_xlsx_output_path is not None:
        export_payment_instructions(records, Path(ok_xlsx_output_path))
        ok_output = str(ok_xlsx_output_path)

    return {
        "run_id": resolved_run_id,
        "xlsx": str(xlsx_output_path),
        "json": str(json_output_path),
        "ok_xlsx": ok_output,
    }


def process_evidence_files(
    file_paths: Iterable[str | Path],
    xlsx_output_path: str | Path,
    json_output_path: str | Path,
    ok_xlsx_output_path: str | Path | None = None,
    run_id: str | None = None,
) -> list[dict]:
    resolved_paths = [Path(path).expanduser().resolve() for path in file_paths]
    records = parse_invoice_files(resolved_paths)
    export_outputs(records, xlsx_output_path, json_output_path, ok_xlsx_output_path, run_id)
    return [record.to_dict() for record in records]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Speer evidence parser")
    parser.add_argument("inputs", nargs="+", help="PDF invoice files")
    parser.add_argument("--xlsx", required=True, help="Output XLSX path")
    parser.add_argument("--json", required=True, help="Output JSON audit log path")
    parser.add_argument("--ok-xlsx", help="Output XLSX path for ok invoices")
    parser.add_argument("--run-id", help="Run ID for audit log")
    args = parser.parse_args()

    process_evidence_files(args.inputs, args.xlsx, args.json, args.ok_xlsx, args.run_id)
