from datetime import date
from typing import Annotated, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.invoice import FileType, InvoiceStatus
from app.models.user import User
from app.schemas.invoice import (
    BulkUploadItemResult,
    BulkUploadResponse,
    InvoiceDetailResponse,
    InvoiceListResponse,
    InvoiceResponse,
)
from app.schemas.invoice_data import (
    CorrectionHistoryResponse,
    InvoiceDataConfidenceResponse,
    InvoiceDataResponse,
    InvoiceDataUpdate,
)
from app.services import invoice_data_service, invoice_service
from app.services.invoice_filters import InvoiceFilters, PaginationParams
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

MAX_BULK_FILES = 20
MAX_PAGE_SIZE = 100

invoice_data_editor = Depends(require_role(["COMPTABLE", "FINANCE", "ADMIN"]))


@router.get("/", response_model=InvoiceListResponse)
async def list_invoices(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Optional[InvoiceStatus] = None,
    file_type: Optional[FileType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    has_duplicate_alert: Optional[bool] = None,
    sort_by: Literal["created_at", "original_filename", "file_size_kb"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> InvoiceListResponse:
    filters = InvoiceFilters(
        status=status,
        file_type=file_type,
        date_from=date_from,
        date_to=date_to,
        has_duplicate_alert=has_duplicate_alert,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pagination = PaginationParams(page=page, page_size=page_size)

    items, total, total_pages = await invoice_service.get_invoices(
        db,
        filters,
        pagination,
        current_user,
    )

    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{invoice_id}/data", response_model=InvoiceDataResponse)
async def get_invoice_data(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvoiceDataResponse:
    data = await invoice_data_service.get_invoice_data(db, invoice_id, current_user)
    return invoice_data_service.to_invoice_data_response(data)


@router.get("/{invoice_id}/data/confidence", response_model=InvoiceDataConfidenceResponse)
async def get_invoice_data_confidence(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvoiceDataConfidenceResponse:
    return await invoice_data_service.get_invoice_data_confidence(
        db, invoice_id, current_user
    )


@router.get("/{invoice_id}/data/history", response_model=CorrectionHistoryResponse)
async def get_invoice_data_history(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, invoice_data_editor],
) -> CorrectionHistoryResponse:
    return await invoice_data_service.get_correction_history(
        db, invoice_id, current_user
    )


@router.put("/{invoice_id}/data", response_model=InvoiceDataResponse)
async def update_invoice_data(
    invoice_id: UUID,
    body: InvoiceDataUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, invoice_data_editor],
) -> InvoiceDataResponse:
    data = await invoice_data_service.update_invoice_data(
        db, invoice_id, body, current_user
    )
    return invoice_data_service.to_invoice_data_response(data)


@router.post("/{invoice_id}/reprocess", response_model=InvoiceResponse)
async def reprocess_invoice(
    invoice_id: UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, invoice_data_editor],
) -> InvoiceResponse:
    invoice = await invoice_service.prepare_invoice_reprocess(
        db, invoice_id, current_user
    )
    background_tasks.add_task(invoice_service.process_invoice_ocr, invoice.id)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvoiceDetailResponse:
    invoice = await invoice_service.get_invoice_by_id(db, invoice_id, current_user)
    return invoice_service.to_detail_response(invoice)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await invoice_service.delete_invoice(db, invoice_id, current_user)


@router.post("/upload", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvoiceResponse:
    settings = get_settings()
    invoice = await invoice_service.create_invoice_from_upload(
        db,
        current_user,
        file,
        settings.UPLOAD_DIR,
    )
    background_tasks.add_task(invoice_service.process_invoice_ocr, invoice.id)
    return invoice


@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_invoices_bulk(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkUploadResponse:
    if len(files) > MAX_BULK_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BULK_FILES} files allowed per bulk upload",
        )

    settings = get_settings()
    results: list[BulkUploadItemResult] = []

    for file in files:
        filename = file.filename or "unknown"
        try:
            invoice = await invoice_service.create_invoice_from_upload(
                db,
                current_user,
                file,
                settings.UPLOAD_DIR,
            )
            background_tasks.add_task(invoice_service.process_invoice_ocr, invoice.id)
            results.append(
                BulkUploadItemResult(
                    filename=filename,
                    status="success",
                    invoice_id=invoice.id,
                )
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            results.append(
                BulkUploadItemResult(
                    filename=filename,
                    status="error",
                    error_message=detail,
                )
            )
        except Exception as exc:
            results.append(
                BulkUploadItemResult(
                    filename=filename,
                    status="error",
                    error_message=str(exc),
                )
            )

    return BulkUploadResponse(results=results)
