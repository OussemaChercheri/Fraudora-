import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.models.supplier_risk_score import SupplierRiskScore
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


def _default_date_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=30), today


def _base_invoice_query(
    user_id: Optional[UUID],
    date_from: date,
    date_to: date,
):
    q = select(Invoice).where(
        cast(Invoice.created_at, Date).between(date_from, date_to)
    )
    if user_id is not None:
        q = q.where(Invoice.user_id == user_id)
    return q


def _resolve_user_filter(current_user: User) -> Optional[UUID]:
    if current_user.role in (UserRole.ADMIN, UserRole.FINANCE):
        return None
    return current_user.id


async def get_dashboard_summary(
    db: AsyncSession,
    current_user: User,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    if date_from is None or date_to is None:
        d_from, d_to = _default_date_range()
        if date_from is None:
            date_from = d_from
        if date_to is None:
            date_to = d_to

    uid = _resolve_user_filter(current_user)

    base = _base_invoice_query(uid, date_from, date_to)

    total_count = await db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    status_rows = (
        await db.execute(
            select(Invoice.status, func.count())
            .where(
                cast(Invoice.created_at, Date).between(date_from, date_to),
            )
            .group_by(Invoice.status)
        )
        if uid is None
        else await db.execute(
            select(Invoice.status, func.count())
            .where(
                Invoice.user_id == uid,
                cast(Invoice.created_at, Date).between(date_from, date_to),
            )
            .group_by(Invoice.status)
        )
    )
    by_status = {s.value: 0 for s in InvoiceStatus}
    for row in status_rows:
        by_status[row.status.value] = row[1]

    result = await db.execute(
        select(func.count()).select_from(
            select(Invoice)
            .where(
                cast(Invoice.created_at, Date).between(date_from, date_to),
                (
                    (Invoice.has_duplicate_alert.is_(True))
                    | (Invoice.has_anomaly_alert.is_(True))
                ),
            )
            .subquery()
        )
    )
    suspectes_count = result.scalar() or 0

    dup_sub = (
        select(Invoice)
        .where(
            cast(Invoice.created_at, Date).between(date_from, date_to),
            Invoice.has_duplicate_alert.is_(True),
        )
        .subquery()
    )
    pending_duplicates = (
        await db.scalar(select(func.count()).select_from(dup_sub)) or 0
    )

    anom_sub = (
        select(Invoice)
        .where(
            cast(Invoice.created_at, Date).between(date_from, date_to),
            Invoice.has_anomaly_alert.is_(True),
        )
        .subquery()
    )
    pending_anomalies = (
        await db.scalar(select(func.count()).select_from(anom_sub)) or 0
    )

    total_pending = pending_duplicates + pending_anomalies

    range_days = (date_to - date_from).days
    if range_days <= 31:
        group_expr = cast(Invoice.created_at, Date)
    else:
        group_expr = func.date_trunc("week", Invoice.created_at)

    evolve_cond = [
        cast(Invoice.created_at, Date).between(date_from, date_to),
    ]
    if uid is not None:
        evolve_cond.append(Invoice.user_id == uid)

    uploaded_rows = (
        await db.execute(
            select(group_expr, func.count())
            .where(*evolve_cond, Invoice.status == InvoiceStatus.UPLOADED)
            .group_by(group_expr)
            .order_by(group_expr)
        )
    ).all()
    processed_rows = (
        await db.execute(
            select(group_expr, func.count())
            .where(
                *evolve_cond,
                Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
            )
            .group_by(group_expr)
            .order_by(group_expr)
        )
    ).all()

    uploaded_map = {str(r[0]): r[1] for r in uploaded_rows}
    processed_map = {str(r[0]): r[1] for r in processed_rows}
    all_labels = sorted(set(uploaded_map.keys()) | set(processed_map.keys()))
    evolution = {
        "labels": all_labels,
        "uploaded": [uploaded_map.get(lbl, 0) for lbl in all_labels],
        "processed": [processed_map.get(lbl, 0) for lbl in all_labels],
    }

    top_fournisseurs_cond = [
        cast(Invoice.created_at, Date).between(date_from, date_to),
    ]
    if uid is not None:
        top_fournisseurs_cond.append(Invoice.user_id == uid)

    top_fournisseurs_rows = (
        await db.execute(
            select(
                InvoiceData.supplier_name,
                func.count().label("invoice_count"),
                func.sum(InvoiceData.total_amount).label("total_amount_sum"),
            )
            .join(Invoice, InvoiceData.invoice_id == Invoice.id)
            .where(*top_fournisseurs_cond, InvoiceData.supplier_name.is_not(None))
            .group_by(InvoiceData.supplier_name)
            .order_by(func.count().desc())
            .limit(5)
        )
    ).all()
    top_fournisseurs = [
        {
            "supplier_name": r.supplier_name,
            "invoice_count": r.invoice_count,
            "total_amount_sum": float(r.total_amount_sum) if r.total_amount_sum else 0,
        }
        for r in top_fournisseurs_rows
    ]

    risques_rows = (
        await db.execute(
            select(SupplierRiskScore)
            .order_by(SupplierRiskScore.risk_score.desc())
            .limit(5)
        )
    ).scalars().all()
    risques = [
        {"supplier_name": r.supplier_name, "risk_score": r.risk_score}
        for r in risques_rows
    ]

    return {
        "factures_totales": {
            "total": total_count,
            "by_status": by_status,
        },
        "alertes": {
            "pending_duplicates": pending_duplicates,
            "pending_anomalies": pending_anomalies,
            "total_pending": total_pending,
        },
        "suspectes": {
            "count": suspectes_count,
        },
        "evolution": evolution,
        "top_fournisseurs": {"items": top_fournisseurs},
        "risques": {"items": risques},
    }
