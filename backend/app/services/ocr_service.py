import logging
import re
import time
from datetime import date, datetime
from uuid import UUID

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.invoice import FileType, Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.services.anomaly_service import run_anomaly_detection
from app.services.duplicate_service import run_duplicate_detection
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.5
MIN_OCR_TEXT_LENGTH = 50

INVOICE_NUMBER_PATTERNS = [
    re.compile(r"N°\s*facture\s*:?\s*([A-Z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"Invoice\s*#?\s*:?\s*([A-Z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"FA[-\s]?(\d{4,})", re.IGNORECASE),
]

INVOICE_DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\ble\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
]

SUPPLIER_LABEL_PATTERN = re.compile(
    r"(?:Fournisseur|Vendor)\s*:?\s*(.+)",
    re.IGNORECASE,
)

TOTAL_AMOUNT_PATTERNS = [
    re.compile(
        r"Total\s*(?:TTC)?\s*:?\s*([\d\s]+[.,]\d{2})\s*(?:DT|TND|EUR|€|\$)?",
        re.IGNORECASE,
    ),
    re.compile(r"Montant\s*total\s*:?\s*([\d\s]+[.,]\d{2})", re.IGNORECASE),
]

TAX_AMOUNT_PATTERNS = [
    re.compile(r"TVA\s*\d*\s*%?\s*:?\s*([\d\s]+[.,]\d{2})", re.IGNORECASE),
    re.compile(r"Tax\s*:?\s*([\d\s]+[.,]\d{2})", re.IGNORECASE),
]

DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
]

INVOICE_NUMBER_VALID = re.compile(r"^[A-Z0-9\-/]+$", re.IGNORECASE)


def convert_to_images(file_path: str, file_type: FileType) -> list[Image.Image]:
    if file_type == FileType.PDF:
        doc = fitz.open(file_path)
        images: list[Image.Image] = []
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
        return images

    with Image.open(file_path) as image:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        return [image.copy()]


def extract_raw_text(images: list[Image.Image], lang: str) -> str:
    pages: list[str] = []
    for index, image in enumerate(images, start=1):
        page_text = pytesseract.image_to_string(
            image,
            lang=lang,
            config="--psm 6",
        )
        pages.append(f"--- PAGE {index} ---\n{page_text.strip()}")
    return "\n\n".join(pages)


def _parse_amount(raw_value: str) -> tuple[float | None, float]:
    cleaned = raw_value.replace(" ", "").replace(",", ".")
    try:
        amount = float(cleaned)
        if amount < 0:
            return None, 0.6
        return amount, 1.0
    except ValueError:
        return None, 0.6


def _parse_date(raw_value: str) -> tuple[str | None, float]:
    value = raw_value.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d"), 1.0
        except ValueError:
            continue
    return None, 0.6


def _extract_invoice_number(raw_text: str) -> tuple[str | None, float]:
    for pattern in INVOICE_NUMBER_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            value = match.group(1).strip().upper()
            if INVOICE_NUMBER_VALID.match(value):
                return value, 1.0
            return value, 0.6
    return None, 0.0


def _extract_invoice_date(raw_text: str) -> tuple[str | None, float]:
    for pattern in INVOICE_DATE_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            iso_date, confidence = _parse_date(match.group(1))
            if iso_date:
                return iso_date, confidence
            return None, 0.6
    return None, 0.0


def _extract_supplier_name(raw_text: str) -> tuple[str | None, float]:
    label_match = SUPPLIER_LABEL_PATTERN.search(raw_text)
    if label_match:
        value = label_match.group(1).strip().split("\n")[0].strip()
        if value:
            return value, 1.0 if value[0].isupper() else 0.6

    facture_index = raw_text.upper().find("FACTURE")
    search_text = raw_text[:facture_index] if facture_index > 0 else raw_text

    for line in search_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate[0].isupper() and len(candidate) > 2:
            if not re.match(r"^\d", candidate):
                return candidate, 1.0

    return None, 0.0


def _extract_total_amount(raw_text: str) -> tuple[float | None, float]:
    for pattern in TOTAL_AMOUNT_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            return _parse_amount(match.group(1))
    return None, 0.0


def _extract_tax_amount(raw_text: str) -> tuple[float | None, float]:
    for pattern in TAX_AMOUNT_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            return _parse_amount(match.group(1))
    return None, 0.0


def extract_invoice_fields(raw_text: str) -> dict:
    invoice_number, invoice_number_conf = _extract_invoice_number(raw_text)
    invoice_date, invoice_date_conf = _extract_invoice_date(raw_text)
    supplier_name, supplier_name_conf = _extract_supplier_name(raw_text)
    total_amount, total_amount_conf = _extract_total_amount(raw_text)
    tax_amount, tax_amount_conf = _extract_tax_amount(raw_text)

    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "supplier_name": supplier_name,
        "total_amount": total_amount,
        "tax_amount": tax_amount,
        "confidence_scores": {
            "invoice_number": invoice_number_conf,
            "invoice_date": invoice_date_conf,
            "supplier_name": supplier_name_conf,
            "total_amount": total_amount_conf,
            "tax_amount": tax_amount_conf,
        },
    }


def _iso_to_date(iso_value: str | None) -> date | None:
    if not iso_value:
        return None
    return datetime.strptime(iso_value, "%Y-%m-%d").date()


def _needs_review(fields: dict, raw_text: str, scores: dict[str, float]) -> bool:
    if any(score < CONFIDENCE_THRESHOLD for score in scores.values()):
        return True
    if fields["total_amount"] is None:
        return True
    if fields["invoice_number"] is None:
        return True
    if len(raw_text.strip()) < MIN_OCR_TEXT_LENGTH:
        return True
    return False


def _set_error(invoice: Invoice, message: str, elapsed_ms: int) -> None:
    invoice.status = InvoiceStatus.ERROR
    invoice.error_message = message[:500]
    invoice.ocr_processing_time_ms = elapsed_ms
    logger.error("OCR failed for invoice %s: %s", invoice.id, message)


async def process_invoice_ocr(
    invoice_id: UUID,
    file_path: str,
    file_type: FileType,
    db: AsyncSession,
) -> None:
    settings = get_settings()
    start = time.time()

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        return

    invoice.status = InvoiceStatus.PROCESSING
    invoice.error_message = None
    await db.commit()

    try:
        images = convert_to_images(file_path, file_type)
        invoice.ocr_page_count = len(images)

        raw_text = extract_raw_text(images, settings.OCR_LANG)
        fields = extract_invoice_fields(raw_text)

        invoice.ocr_raw_text = raw_text

        existing_data = await db.execute(
            select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
        )
        invoice_data = existing_data.scalar_one_or_none()
        if invoice_data is None:
            invoice_data = InvoiceData(invoice_id=invoice_id)
            db.add(invoice_data)

        invoice_data.invoice_number = fields["invoice_number"]
        invoice_data.invoice_date = _iso_to_date(fields["invoice_date"])
        invoice_data.supplier_name = fields["supplier_name"]
        invoice_data.total_amount = fields["total_amount"]
        invoice_data.tax_amount = fields["tax_amount"]

        scores = fields["confidence_scores"]
        invoice_data.confidence_invoice_number = scores["invoice_number"]
        invoice_data.confidence_invoice_date = scores["invoice_date"]
        invoice_data.confidence_supplier_name = scores["supplier_name"]
        invoice_data.confidence_total_amount = scores["total_amount"]
        invoice_data.confidence_tax_amount = scores["tax_amount"]

        invoice.status = (
            InvoiceStatus.REVIEW_REQUIRED
            if _needs_review(fields, raw_text, scores)
            else InvoiceStatus.PROCESSED
        )
        invoice.error_message = None

        if invoice.status in (InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED):
            duplicate_result = await run_duplicate_detection(db, invoice_id)
            logger.info("Duplicate check for %s: %s", invoice_id, duplicate_result)

            anomaly_result = await run_anomaly_detection(db, invoice_id)
            logger.info("Anomaly check for %s: %s", invoice_id, anomaly_result)

    except FileNotFoundError:
        _set_error(invoice, "File not found on disk", int((time.time() - start) * 1000))
    except pytesseract.pytesseract.TesseractNotFoundError:
        _set_error(invoice, "Tesseract not installed", int((time.time() - start) * 1000))
    except UnidentifiedImageError:
        _set_error(invoice, "Unreadable image file", int((time.time() - start) * 1000))
    except Exception as exc:
        logger.exception("OCR pipeline failed for invoice %s", invoice_id)
        _set_error(invoice, str(exc)[:500], int((time.time() - start) * 1000))
    else:
        invoice.ocr_processing_time_ms = int((time.time() - start) * 1000)

    # Notify user of final status
    if invoice.status == InvoiceStatus.PROCESSED:
        await create_notification(
            db,
            user_id=invoice.user_id,
            title="Facture traitée",
            message=f"{invoice.original_filename} a été traité avec succès",
            notification_type="INVOICE_PROCESSED",
            related_invoice_id=invoice_id,
        )
    elif invoice.status == InvoiceStatus.ERROR:
        await create_notification(
            db,
            user_id=invoice.user_id,
            title="Erreur de traitement",
            message=f"Erreur OCR sur {invoice.original_filename}: {invoice.error_message}",
            notification_type="INVOICE_ERROR",
            related_invoice_id=invoice_id,
        )

    await db.commit()
