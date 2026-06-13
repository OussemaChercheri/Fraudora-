from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.models.user import User, UserRole

PROCESSED_STATUSES = {InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED}


def _months_ago(months: int) -> datetime:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def _invoice_data_base_query(user_id: Optional[UUID]):
    query = select(InvoiceData).join(Invoice, InvoiceData.invoice_id == Invoice.id)
    if user_id is not None:
        query = query.where(Invoice.user_id == user_id)
    return query


async def get_processing_summary(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
) -> dict:
    base = select(Invoice)
    if user_id is not None:
        base = base.where(Invoice.user_id == user_id)

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    status_counts = {status.value: 0 for status in InvoiceStatus}
    for status in InvoiceStatus:
        count_query = select(func.count()).select_from(Invoice).where(Invoice.status == status)
        if user_id is not None:
            count_query = count_query.where(Invoice.user_id == user_id)
        status_counts[status.value] = await db.scalar(count_query) or 0

    avg_time_query = select(func.avg(Invoice.ocr_processing_time_ms)).where(
        Invoice.ocr_processing_time_ms.is_not(None)
    )
    if user_id is not None:
        avg_time_query = avg_time_query.where(Invoice.user_id == user_id)
    avg_processing_time_ms = await db.scalar(avg_time_query)

    pages_query = select(func.coalesce(func.sum(Invoice.ocr_page_count), 0)).where(
        Invoice.ocr_page_count.is_not(None)
    )
    if user_id is not None:
        pages_query = pages_query.where(Invoice.user_id == user_id)
    total_pages_processed = await db.scalar(pages_query) or 0

    def _rate(count: int) -> float:
        if total == 0:
            return 0.0
        return round(count / total * 100, 2)

    return {
        "total_invoices": total,
        "by_status": status_counts,
        "processed_rate": _rate(status_counts[InvoiceStatus.PROCESSED.value]),
        "review_required_rate": _rate(status_counts[InvoiceStatus.REVIEW_REQUIRED.value]),
        "error_rate": _rate(status_counts[InvoiceStatus.ERROR.value]),
        "avg_processing_time_ms": round(float(avg_processing_time_ms or 0), 2),
        "total_pages_processed": int(total_pages_processed),
    }


async def get_ocr_quality_stats(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
) -> dict:
    data_query = _invoice_data_base_query(user_id)
    subq = data_query.subquery()

    total_data = await db.scalar(select(func.count()).select_from(subq)) or 0

    avg_confidence = {}
    field_extraction_rate = {}
    fields = {
        "invoice_number": (InvoiceData.invoice_number, InvoiceData.confidence_invoice_number),
        "invoice_date": (InvoiceData.invoice_date, InvoiceData.confidence_invoice_date),
        "supplier_name": (InvoiceData.supplier_name, InvoiceData.confidence_supplier_name),
        "total_amount": (InvoiceData.total_amount, InvoiceData.confidence_total_amount),
        "tax_amount": (InvoiceData.tax_amount, InvoiceData.confidence_tax_amount),
    }

    for field_name, (value_col, confidence_col) in fields.items():
        avg_query = select(func.avg(confidence_col)).select_from(InvoiceData).join(
            Invoice, InvoiceData.invoice_id == Invoice.id
        )
        count_query = select(func.count()).select_from(InvoiceData).join(
            Invoice, InvoiceData.invoice_id == Invoice.id
        ).where(value_col.is_not(None))

        if user_id is not None:
            avg_query = avg_query.where(Invoice.user_id == user_id)
            count_query = count_query.where(Invoice.user_id == user_id)

        avg_val = await db.scalar(avg_query)
        extracted_count = await db.scalar(count_query) or 0

        avg_confidence[field_name] = round(float(avg_val or 0), 4)
        field_extraction_rate[field_name] = (
            round(extracted_count / total_data * 100, 2) if total_data > 0 else 0.0
        )

    corrected_query = select(func.count()).select_from(InvoiceData).join(
        Invoice, InvoiceData.invoice_id == Invoice.id
    ).where(InvoiceData.is_manually_corrected.is_(True))
    if user_id is not None:
        corrected_query = corrected_query.where(Invoice.user_id == user_id)
    manually_corrected_count = await db.scalar(corrected_query) or 0

    processed_query = select(func.count()).select_from(Invoice).where(
        Invoice.status.in_(PROCESSED_STATUSES)
    )
    if user_id is not None:
        processed_query = processed_query.where(Invoice.user_id == user_id)
    processed_count = await db.scalar(processed_query) or 0

    manually_corrected_rate = (
        round(manually_corrected_count / processed_count * 100, 2)
        if processed_count > 0
        else 0.0
    )

    return {
        "avg_confidence": avg_confidence,
        "field_extraction_rate": field_extraction_rate,
        "manually_corrected_count": manually_corrected_count,
        "manually_corrected_rate": manually_corrected_rate,
    }


async def get_supplier_summary(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
) -> list[dict]:
    query = (
        select(
            InvoiceData.supplier_name,
            func.count(InvoiceData.id).label("invoice_count"),
            func.sum(InvoiceData.total_amount).label("total_amount_sum"),
            func.avg(InvoiceData.total_amount).label("avg_amount"),
            func.min(InvoiceData.total_amount).label("min_amount"),
            func.max(InvoiceData.total_amount).label("max_amount"),
            func.min(InvoiceData.invoice_date).label("first_seen"),
            func.max(InvoiceData.invoice_date).label("last_seen"),
        )
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.supplier_name.is_not(None),
            Invoice.status.in_(PROCESSED_STATUSES),
        )
        .group_by(InvoiceData.supplier_name)
        .order_by(func.count(InvoiceData.id).desc())
        .limit(50)
    )

    if user_id is not None:
        query = query.where(Invoice.user_id == user_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "supplier_name": row.supplier_name,
            "invoice_count": row.invoice_count,
            "total_amount_sum": round(float(row.total_amount_sum or 0), 3),
            "avg_amount": round(float(row.avg_amount or 0), 3),
            "min_amount": round(float(row.min_amount or 0), 3),
            "max_amount": round(float(row.max_amount or 0), 3),
            "first_seen": row.first_seen,
            "last_seen": row.last_seen,
        }
        for row in rows
    ]


async def get_monthly_volume(
    db: AsyncSession,
    months: int = 6,
    user_id: Optional[UUID] = None,
) -> list[dict]:
    month_expr = func.to_char(Invoice.created_at, "YYYY-MM")

    start_date = _months_ago(months)

    query = (
        select(
            month_expr.label("month"),
            func.count(Invoice.id).label("count"),
            func.sum(
                case(
                    (Invoice.status.in_(PROCESSED_STATUSES), 1),
                    else_=0,
                )
            ).label("processed_count"),
        )
        .where(Invoice.created_at >= start_date)
        .group_by(month_expr)
        .order_by(month_expr)
    )

    if user_id is not None:
        query = query.where(Invoice.user_id == user_id)

    result = await db.execute(query)
    db_rows = {row.month: row for row in result.all()}

    now = datetime.now(timezone.utc)
    output: list[dict] = []
    for offset in range(months - 1, -1, -1):
        year = now.year
        month = now.month - offset
        while month <= 0:
            month += 12
            year -= 1
        key = f"{year:04d}-{month:02d}"
        row = db_rows.get(key)
        output.append(
            {
                "month": key,
                "count": int(row.count) if row else 0,
                "processed_count": int(row.processed_count) if row else 0,
            }
        )

    return output


def _generate_bucket_labels(d_from: date, d_to: date, granularity: str) -> list[str]:
    labels: list[str] = []
    current = d_from
    if granularity == "week":
        current = d_from - timedelta(days=d_from.weekday())
    while current <= d_to:
        if granularity == "month":
            labels.append(current.strftime("%Y-%m"))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        elif granularity == "week":
            labels.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=7)
        else:
            labels.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
    return labels


def _query_expense_period(
    rows: list,
    labels: list[str],
    granularity: str,
) -> list[dict]:
    label_key: str
    if granularity == "month":
        def mk_label(d):
            return d.strftime("%Y-%m")
    elif granularity == "week":
        def mk_label(d):
            return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")
    else:
        def mk_label(d):
            return d.strftime("%Y-%m-%d")

    buckets: dict[str, float] = {lbl: 0.0 for lbl in labels}
    for row in rows:
        d, amt = row
        if d is None or amt is None:
            continue
        key = mk_label(d)
        if key in buckets:
            buckets[key] += float(amt)

    total = sum(buckets.values())
    return {
        "total": round(total, 3),
        "buckets": [
            {"period_label": lbl, "amount": round(buckets[lbl], 3)}
            for lbl in labels
        ],
    }


async def get_expense_evolution(
    db: AsyncSession,
    current_user: User,
    date_from: date,
    date_to: date,
    granularity: str = "month",
) -> dict:
    period_n_days = (date_to - date_from).days
    n_minus_1_to = date_from - timedelta(days=1)
    n_minus_1_from = n_minus_1_to - timedelta(days=period_n_days)

    labels = _generate_bucket_labels(date_from, date_to, granularity)

    user_id: Optional[UUID] = None
    if current_user.role == UserRole.COMPTABLE:
        user_id = current_user.id

    async def _fetch_period(d_from: date, d_to: date) -> list:
        query = (
            select(
                InvoiceData.invoice_date,
                InvoiceData.total_amount,
            )
            .join(Invoice, InvoiceData.invoice_id == Invoice.id)
            .where(
                Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
                InvoiceData.invoice_date.isnot(None),
                InvoiceData.invoice_date >= d_from,
                InvoiceData.invoice_date <= d_to,
            )
            .order_by(InvoiceData.invoice_date)
        )
        if user_id is not None:
            query = query.where(Invoice.user_id == user_id)
        result = await db.execute(query)
        return result.all()

    rows_n = await _fetch_period(date_from, date_to)
    rows_n_1 = await _fetch_period(n_minus_1_from, n_minus_1_to)

    period_n = _query_expense_period(rows_n, labels, granularity)
    period_n_minus_1 = _query_expense_period(rows_n_1, labels, granularity)

    total_n = period_n["total"]
    total_n_1 = period_n_minus_1["total"]
    if total_n_1 > 0:
        variation_pct = round((total_n - total_n_1) / total_n_1 * 100, 2)
    elif total_n > 0:
        variation_pct = 999999.99
    else:
        variation_pct = 0.0

    if variation_pct > 5:
        direction = "hausse"
    elif variation_pct < -5:
        direction = "baisse"
    else:
        direction = "stable"

    return {
        "period_n": {
            "label": f"{date_from} - {date_to}",
            **period_n,
        },
        "period_n_minus_1": {
            "label": f"{n_minus_1_from} - {n_minus_1_to}",
            **period_n_minus_1,
        },
        "variation_pct": variation_pct,
        "variation_direction": direction,
    }
