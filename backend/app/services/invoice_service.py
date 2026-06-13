import logging
import math
from datetime import datetime, time, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.invoice import FileType, Invoice, InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.invoice import InvoiceDetailResponse
from app.services import ocr_service
from app.services.file_service import delete_file, save_file, validate_file
from app.services.invoice_filters import InvoiceFilters, PaginationParams

logger = logging.getLogger(__name__)


def _can_view_all_invoices(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.FINANCE}


def _build_filter_conditions(filters: InvoiceFilters, current_user: User) -> list:
    conditions = []

    if not _can_view_all_invoices(current_user):
        conditions.append(Invoice.user_id == current_user.id)

    if filters.status is not None:
        conditions.append(Invoice.status == filters.status)

    if filters.file_type is not None:
        conditions.append(Invoice.file_type == filters.file_type)

    if filters.date_from is not None:
        start = datetime.combine(filters.date_from, time.min, tzinfo=timezone.utc)
        conditions.append(Invoice.created_at >= start)

    if filters.date_to is not None:
        end = datetime.combine(filters.date_to, time.max, tzinfo=timezone.utc)
        conditions.append(Invoice.created_at <= end)

    if filters.has_duplicate_alert is not None:
        conditions.append(Invoice.has_duplicate_alert == filters.has_duplicate_alert)

    if filters.has_anomaly_alert is not None:
        conditions.append(Invoice.has_anomaly_alert == filters.has_anomaly_alert)

    return conditions


def _extension_to_file_type(extension: str) -> FileType:
    if extension == ".pdf":
        return FileType.PDF
    if extension in {".jpg", ".jpeg"}:
        return FileType.JPG
    return FileType.PNG


def to_detail_response(invoice: Invoice) -> InvoiceDetailResponse:
    return InvoiceDetailResponse(
        id=invoice.id,
        user_id=invoice.user_id,
        original_filename=invoice.original_filename,
        file_type=invoice.file_type,
        file_size_kb=invoice.file_size_kb,
        status=invoice.status,
        has_duplicate_alert=invoice.has_duplicate_alert,
        is_duplicate_confirmed=invoice.is_duplicate_confirmed,
        has_anomaly_alert=invoice.has_anomaly_alert,
        created_at=invoice.created_at,
        ocr_raw_text=invoice.ocr_raw_text
        if invoice.status in {InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED}
        else None,
    )


async def create_invoice_from_upload(
    db: AsyncSession,
    user: User,
    file: UploadFile,
    upload_dir: str,
) -> Invoice:
    await validate_file(file)
    stored_filename, file_path, file_size_kb = await save_file(file, upload_dir)
    extension = Path(file.filename).suffix.lower()

    invoice = Invoice(
        user_id=user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_type=_extension_to_file_type(extension),
        file_size_kb=file_size_kb,
        status=InvoiceStatus.UPLOADED,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def get_invoices(
    db: AsyncSession,
    filters: InvoiceFilters,
    pagination: PaginationParams,
    current_user: User,
) -> tuple[list[Invoice], int, int]:
    conditions = _build_filter_conditions(filters, current_user)

    total = await db.scalar(
        select(func.count()).select_from(Invoice).where(*conditions)
    )
    total = total or 0
    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0

    sort_column = getattr(Invoice, filters.sort_by)
    order = sort_column.asc() if filters.sort_order == "asc" else sort_column.desc()
    offset = (pagination.page - 1) * pagination.page_size

    result = await db.execute(
        select(Invoice)
        .where(*conditions)
        .order_by(order)
        .offset(offset)
        .limit(pagination.page_size)
    )
    items = list(result.scalars().all())
    return items, total, total_pages


async def get_invoice_by_id(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if not _can_view_all_invoices(current_user) and invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    return invoice


async def update_invoice_status(
    db: AsyncSession,
    invoice_id: UUID,
    new_status: InvoiceStatus,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    invoice.status = new_status
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def delete_invoice(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> None:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    is_owner = invoice.user_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this invoice",
        )

    delete_file(invoice.file_path)
    await db.delete(invoice)
    await db.commit()


async def process_invoice_ocr(invoice_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if invoice is None:
            return

        await ocr_service.process_invoice_ocr(
            invoice_id,
            invoice.file_path,
            invoice.file_type,
            db,
        )


async def prepare_invoice_reprocess(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> Invoice:
    invoice = await get_invoice_by_id(db, invoice_id, current_user)

    if invoice.status not in {InvoiceStatus.ERROR, InvoiceStatus.REVIEW_REQUIRED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice can only be reprocessed when status is ERROR or REVIEW_REQUIRED",
        )

    invoice.status = InvoiceStatus.UPLOADED
    invoice.error_message = None
    invoice.ocr_page_count = None
    invoice.ocr_processing_time_ms = None
    await db.commit()
    await db.refresh(invoice)
    return invoice
