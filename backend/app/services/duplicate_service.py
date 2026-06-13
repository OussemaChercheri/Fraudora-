import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from rapidfuzz import fuzz
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.duplicate_match import DuplicateMatch, DuplicateStatus, MatchType
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.models.user import User, UserRole
from app.schemas.duplicate_match import (
    DuplicateMatchResponse,
    DuplicateReviewRequest,
    InvoiceSummary,
)
from app.services.notification_service import (
    create_notification,
    get_finance_and_admin_user_ids,
)
from app.services.threshold_service import get_threshold_value

logger = logging.getLogger(__name__)


async def detect_exact_duplicates(
    db: AsyncSession,
    invoice_id: UUID,
) -> list[DuplicateMatch]:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        return []

    data_result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    invoice_data = data_result.scalar_one_or_none()
    if invoice_data is None or not invoice_data.invoice_number:
        return []

    current_number = invoice_data.invoice_number.strip()
    if not current_number:
        return []

    current_lower = current_number.lower()

    matches_query = await db.execute(
        select(InvoiceData)
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            and_(
                InvoiceData.invoice_id != invoice_id,
                Invoice.status != InvoiceStatus.ERROR,
                func.lower(InvoiceData.invoice_number) == current_lower,
            )
        )
    )
    matched_data_rows = matches_query.scalars().all()

    existing_matches_query = await db.execute(
        select(DuplicateMatch).where(
            or_(
                and_(
                    DuplicateMatch.invoice_id == invoice_id,
                    DuplicateMatch.matched_invoice_id.in_(
                        [row.invoice_id for row in matched_data_rows]
                    ),
                ),
                and_(
                    DuplicateMatch.matched_invoice_id == invoice_id,
                    DuplicateMatch.invoice_id.in_(
                        [row.invoice_id for row in matched_data_rows]
                    ),
                ),
            )
        )
    )
    existing = existing_matches_query.scalars().all()
    existing_pairs: set[tuple[UUID, UUID]] = set()
    for em in existing:
        existing_pairs.add((em.invoice_id, em.matched_invoice_id))

    created: list[DuplicateMatch] = []
    for row in matched_data_rows:
        pair = (invoice_id, row.invoice_id)
        reverse_pair = (row.invoice_id, invoice_id)
        if pair in existing_pairs or reverse_pair in existing_pairs:
            continue

        match = DuplicateMatch(
            invoice_id=invoice_id,
            matched_invoice_id=row.invoice_id,
            match_type=MatchType.EXACT_NUMBER,
            similarity_score=100.0,
            status=DuplicateStatus.PENDING,
        )
        db.add(match)
        created.append(match)

    if created:
        invoice.has_duplicate_alert = True
        invoice.status = InvoiceStatus.REVIEW_REQUIRED

    await db.flush()

    if created:
        logger.info(
            "Detected %d exact duplicate(s) for invoice %s (number=%s)",
            len(created),
            invoice_id,
            current_number,
        )

        recipient_ids = [invoice.user_id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        recipient_ids = list(set(recipient_ids))

        for uid in recipient_ids:
            await create_notification(
                db,
                user_id=uid,
                title="Doublon potentiel détecté",
                message=(
                    f"La facture {invoice.original_filename} est un doublon exact "
                    f"d'une facture existante"
                ),
                notification_type="DUPLICATE_ALERT",
                related_invoice_id=invoice_id,
            )

    return created


async def _get_existing_pairs_for_invoice(
    db: AsyncSession,
    invoice_id: UUID,
) -> set[tuple[UUID, UUID]]:
    existing_result = await db.execute(
        select(DuplicateMatch).where(
            or_(
                DuplicateMatch.invoice_id == invoice_id,
                DuplicateMatch.matched_invoice_id == invoice_id,
            )
        )
    )
    existing = existing_result.scalars().all()
    pairs: set[tuple[UUID, UUID]] = set()
    for em in existing:
        pairs.add((em.invoice_id, em.matched_invoice_id))
    return pairs


async def detect_fuzzy_duplicates(
    db: AsyncSession,
    invoice_id: UUID,
) -> list[DuplicateMatch]:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        return []

    data_result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    current = data_result.scalar_one_or_none()
    if current is None:
        return []

    if current.supplier_name is None and current.total_amount is None:
        return []

    threshold = await get_threshold_value(db, "fuzzy_duplicate_similarity", 85.0)

    candidates_query = await db.execute(
        select(InvoiceData)
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            and_(
                InvoiceData.invoice_id != invoice_id,
                Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
                InvoiceData.supplier_name.isnot(None),
            )
        )
    )
    candidates = candidates_query.scalars().all()

    existing_pairs = await _get_existing_pairs_for_invoice(db, invoice_id)

    created: list[DuplicateMatch] = []
    for candidate in candidates:
        pair = (invoice_id, candidate.invoice_id)
        reverse_pair = (candidate.invoice_id, invoice_id)
        if pair in existing_pairs or reverse_pair in existing_pairs:
            continue

        supp_sim: float = 0.0
        if current.supplier_name and candidate.supplier_name:
            supp_sim = fuzz.token_sort_ratio(
                current.supplier_name, candidate.supplier_name
            )

        amt_sim: float = 0.0
        if current.total_amount is not None and candidate.total_amount is not None:
            cur_amt = float(current.total_amount)
            cand_amt = float(candidate.total_amount)
            divisor = max(cur_amt, cand_amt, 1.0)
            diff_pct = abs(cur_amt - cand_amt) / divisor * 100.0
            amt_sim = max(0.0, 100.0 - diff_pct * 2.0)

        date_sim: float = 50.0
        if current.invoice_date is not None and candidate.invoice_date is not None:
            day_diff = abs((current.invoice_date - candidate.invoice_date).days)
            date_sim = max(0.0, 100.0 - day_diff * 10.0)

        composite = (supp_sim * 0.5) + (amt_sim * 0.35) + (date_sim * 0.15)

        if composite < threshold:
            continue

        match = DuplicateMatch(
            invoice_id=invoice_id,
            matched_invoice_id=candidate.invoice_id,
            match_type=MatchType.FUZZY_SIMILARITY,
            similarity_score=round(composite, 2),
            status=DuplicateStatus.PENDING,
        )
        db.add(match)
        created.append(match)

    if created:
        invoice.has_duplicate_alert = True
        invoice.status = InvoiceStatus.REVIEW_REQUIRED

    await db.flush()

    if created:
        logger.info(
            "Detected %d fuzzy duplicate(s) for invoice %s",
            len(created),
            invoice_id,
        )

        recipient_ids = [invoice.user_id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        recipient_ids = list(set(recipient_ids))

        for uid in recipient_ids:
            for match in created:
                await create_notification(
                    db,
                    user_id=uid,
                    title="Doublon potentiel détecté",
                    message=(
                        f"La facture {invoice.original_filename} ressemble à "
                        f"une facture existante ({match.similarity_score}%)"
                    ),
                    notification_type="DUPLICATE_ALERT",
                    related_invoice_id=invoice_id,
                )

    return created


async def run_duplicate_detection(
    db: AsyncSession,
    invoice_id: UUID,
) -> dict[str, int]:
    exact_matches = await detect_exact_duplicates(db, invoice_id)
    fuzzy_matches = await detect_fuzzy_duplicates(db, invoice_id)
    return {
        "exact_matches": len(exact_matches),
        "fuzzy_matches": len(fuzzy_matches),
    }


async def _build_invoice_summary(db: AsyncSession, invoice_id: UUID) -> InvoiceSummary:
    inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if invoice is None:
        return InvoiceSummary(id=invoice_id, original_filename="")

    data_result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    data = data_result.scalar_one_or_none()
    total_amount: Optional[float] = None
    if data and data.total_amount is not None:
        total_amount = float(data.total_amount)

    return InvoiceSummary(
        id=invoice.id,
        original_filename=invoice.original_filename,
        invoice_number=data.invoice_number if data else None,
        supplier_name=data.supplier_name if data else None,
        total_amount=total_amount,
        invoice_date=data.invoice_date if data else None,
    )


async def _match_to_response(
    db: AsyncSession, match: DuplicateMatch
) -> DuplicateMatchResponse:
    invoice_summary = await _build_invoice_summary(db, match.invoice_id)
    matched_summary = await _build_invoice_summary(db, match.matched_invoice_id)
    return DuplicateMatchResponse(
        id=match.id,
        invoice_id=match.invoice_id,
        matched_invoice_id=match.matched_invoice_id,
        match_type=match.match_type,
        similarity_score=match.similarity_score,
        status=match.status,
        rejection_reason=match.rejection_reason,
        reviewed_by_user_id=match.reviewed_by_user_id,
        reviewed_at=match.reviewed_at,
        created_at=match.created_at,
        invoice=invoice_summary,
        matched_invoice=matched_summary,
    )


async def get_duplicate_matches(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> list[DuplicateMatchResponse]:
    result = await db.execute(
        select(DuplicateMatch).where(
            or_(
                DuplicateMatch.invoice_id == invoice_id,
                DuplicateMatch.matched_invoice_id == invoice_id,
            )
        )
    )
    matches = result.scalars().all()

    if current_user.role not in (UserRole.ADMIN, UserRole.FINANCE):
        inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = inv_result.scalar_one_or_none()
        if invoice is None or invoice.user_id != current_user.id:
            return []

    return [await _match_to_response(db, m) for m in matches]


async def review_duplicate_match(
    db: AsyncSession,
    match_id: UUID,
    review: DuplicateReviewRequest,
    current_user: User,
) -> DuplicateMatchResponse:
    result = await db.execute(select(DuplicateMatch).where(DuplicateMatch.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Duplicate match not found",
        )

    match.status = DuplicateStatus(review.status)
    if review.status == DuplicateStatus.REJECTED.value:
        match.rejection_reason = review.rejection_reason

    match.reviewed_by_user_id = current_user.id
    match.reviewed_at = datetime.now(timezone.utc)

    if review.status == DuplicateStatus.CONFIRMED_DUPLICATE.value:
        inv_result = await db.execute(
            select(Invoice).where(Invoice.id == match.invoice_id)
        )
        invoice = inv_result.scalar_one_or_none()
        if invoice is not None:
            invoice.is_duplicate_confirmed = True

    pending_result = await db.execute(
        select(func.count()).select_from(DuplicateMatch).where(
            and_(
                or_(
                    DuplicateMatch.invoice_id == match.invoice_id,
                    DuplicateMatch.matched_invoice_id == match.invoice_id,
                ),
                DuplicateMatch.status == DuplicateStatus.PENDING,
            )
        )
    )
    pending_count = pending_result.scalar() or 0

    if pending_count == 0:
        inv_result = await db.execute(
            select(Invoice).where(Invoice.id == match.invoice_id)
        )
        invoice = inv_result.scalar_one_or_none()
        if invoice is not None and invoice.status == InvoiceStatus.REVIEW_REQUIRED:
            data_result = await db.execute(
                select(InvoiceData).where(InvoiceData.invoice_id == match.invoice_id)
            )
            data = data_result.scalar_one_or_none()
            if data is not None:
                scores = [
                    data.confidence_invoice_number,
                    data.confidence_invoice_date,
                    data.confidence_supplier_name,
                    data.confidence_total_amount,
                    data.confidence_tax_amount,
                ]
                if all(s >= 0.5 for s in scores) and data.invoice_number is not None and data.total_amount is not None:
                    invoice.status = InvoiceStatus.PROCESSED

    await db.flush()
    return await _match_to_response(db, match)


async def get_duplicate_summary_for_invoice(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> dict:
    result = await db.execute(
        select(DuplicateMatch).where(
            or_(
                DuplicateMatch.invoice_id == invoice_id,
                DuplicateMatch.matched_invoice_id == invoice_id,
            )
        )
    )
    matches = result.scalars().all()

    if current_user.role not in (UserRole.ADMIN, UserRole.FINANCE):
        inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = inv_result.scalar_one_or_none()
        if invoice is None or invoice.user_id != current_user.id:
            return {
                "total_matches": 0,
                "pending": 0,
                "confirmed": 0,
                "rejected": 0,
                "highest_similarity": 0.0,
            }

    total = len(matches)
    pending = sum(1 for m in matches if m.status == DuplicateStatus.PENDING)
    confirmed = sum(1 for m in matches if m.status == DuplicateStatus.CONFIRMED_DUPLICATE)
    rejected = sum(1 for m in matches if m.status == DuplicateStatus.REJECTED)
    highest = max((m.similarity_score for m in matches), default=0.0)

    return {
        "total_matches": total,
        "pending": pending,
        "confirmed": confirmed,
        "rejected": rejected,
        "highest_similarity": highest,
    }


async def get_pending_matches_paginated(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DuplicateMatchResponse], int, int]:
    conditions = [DuplicateMatch.status == DuplicateStatus.PENDING]

    if current_user.role not in (UserRole.ADMIN, UserRole.FINANCE):
        conditions.append(
            or_(
                DuplicateMatch.invoice_id.in_(
                    select(Invoice.id).where(Invoice.user_id == current_user.id)
                ),
                DuplicateMatch.matched_invoice_id.in_(
                    select(Invoice.id).where(Invoice.user_id == current_user.id)
                ),
            )
        )

    total_result = await db.execute(
        select(func.count()).select_from(DuplicateMatch).where(*conditions)
    )
    total = total_result.scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    matches_result = await db.execute(
        select(DuplicateMatch)
        .where(*conditions)
        .order_by(DuplicateMatch.similarity_score.desc(), DuplicateMatch.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    matches = matches_result.scalars().all()

    responses = [await _match_to_response(db, m) for m in matches]
    return responses, total, total_pages
