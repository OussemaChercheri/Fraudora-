import logging
from datetime import date, datetime, timezone
from uuid import UUID

import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly_alert import AlertStatus, AlertType, AnomalyAlert, Severity
from app.models.duplicate_match import DuplicateMatch, DuplicateStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.models.supplier_risk_score import SupplierRiskScore
from app.models.user import User, UserRole
from app.schemas.anomaly_alert import AnomalyAlertResponse, AnomalyAcknowledgeRequest, InvoiceSummary
from app.services.notification_service import (
    create_notification,
    get_finance_and_admin_user_ids,
)
from app.services.threshold_service import get_threshold_value

logger = logging.getLogger(__name__)


async def detect_abnormal_amount(
    db: AsyncSession,
    invoice_id: UUID,
) -> AnomalyAlert | None:
    data_result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    current = data_result.scalar_one_or_none()
    if current is None or current.supplier_name is None or current.total_amount is None:
        return None

    supplier = current.supplier_name.strip()
    current_amount = float(current.total_amount)

    historical = await db.execute(
        select(InvoiceData.total_amount)
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.invoice_id != invoice_id,
            InvoiceData.supplier_name.isnot(None),
            func.trim(func.lower(InvoiceData.supplier_name)) == supplier.lower(),
            InvoiceData.total_amount.isnot(None),
            Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
        )
    )
    amounts = [float(row[0]) for row in historical.all()]

    if len(amounts) < 3:
        return None

    mean = float(np.mean(amounts))
    std = float(np.std(amounts, ddof=0))

    if std == 0:
        std = mean * 0.05

    z_score = (current_amount - mean) / std

    zscore_threshold = await get_threshold_value(db, "abnormal_amount_zscore", 2.0)
    if z_score <= zscore_threshold:
        return None

    threshold = mean + zscore_threshold * std
    severity = Severity.HIGH if z_score > 3.0 else Severity.MEDIUM
    description = (
        f"Montant de {current_amount} TND dépasse la moyenne habituelle de {mean:.2f} TND "
        f"pour {supplier} (seuil: moyenne + 2 écarts-types = {threshold:.2f} TND)"
    )

    alert = AnomalyAlert(
        invoice_id=invoice_id,
        alert_type=AlertType.ABNORMAL_AMOUNT,
        severity=severity,
        description=description,
        metric_value=round(float(z_score), 2),
        threshold_value=round(float(threshold), 2),
        status=AlertStatus.PENDING,
    )
    db.add(alert)

    inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if invoice is not None:
        invoice.has_anomaly_alert = True
        if invoice.status != InvoiceStatus.REVIEW_REQUIRED:
            invoice.status = InvoiceStatus.REVIEW_REQUIRED

    await db.flush()
    logger.info(
        "ABNORMAL_AMOUNT alert for invoice %s: z=%.2f, supplier=%s",
        invoice_id,
        z_score,
        supplier,
    )

    if invoice is not None:
        recipient_ids = [invoice.user_id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        for uid in set(recipient_ids):
            await create_notification(
                db,
                user_id=uid,
                title="Anomalie détectée",
                message=description,
                notification_type="ANOMALY_ALERT",
                related_invoice_id=invoice_id,
            )

    return alert


async def detect_new_high_risk_supplier(
    db: AsyncSession,
    invoice_id: UUID,
) -> AnomalyAlert | None:
    data_result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    current = data_result.scalar_one_or_none()
    if current is None or current.supplier_name is None:
        return None

    supplier = current.supplier_name.strip()
    current_date = current.invoice_date

    historical = await db.execute(
        select(InvoiceData.invoice_date)
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.invoice_id != invoice_id,
            InvoiceData.supplier_name.isnot(None),
            func.trim(func.lower(InvoiceData.supplier_name)) == supplier.lower(),
            Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
            InvoiceData.invoice_date.isnot(None),
        )
        .order_by(InvoiceData.invoice_date.desc())
        .limit(1)
    )
    most_recent = historical.scalar_one_or_none()

    alert: AnomalyAlert | None = None

    if most_recent is None:
        alert = AnomalyAlert(
            invoice_id=invoice_id,
            alert_type=AlertType.NEW_HIGH_RISK_SUPPLIER,
            severity=Severity.MEDIUM,
            description=(
                f"Nouveau fournisseur détecté : '{supplier}' "
                f"n'a jamais été référencé auparavant. Vérification recommandée."
            ),
            metric_value=0,
            threshold_value=0,
            status=AlertStatus.PENDING,
        )
        db.add(alert)
    else:
        if current_date is None:
            return None
        days_diff = (current_date - most_recent).days
        dormant_threshold = await get_threshold_value(db, "dormant_supplier_days", 180.0)
        if days_diff > dormant_threshold:
            alert = AnomalyAlert(
                invoice_id=invoice_id,
                alert_type=AlertType.NEW_HIGH_RISK_SUPPLIER,
                severity=Severity.HIGH,
                description=(
                    f"Fournisseur '{supplier}' non référencé depuis {days_diff} jours "
                    f"(> 6 mois). Facture inhabituelle, vérification recommandée."
                ),
                metric_value=days_diff,
                threshold_value=180,
                status=AlertStatus.PENDING,
            )
            db.add(alert)

    if alert is not None:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = inv_result.scalar_one_or_none()
        if invoice is not None:
            invoice.has_anomaly_alert = True
            if invoice.status != InvoiceStatus.REVIEW_REQUIRED:
                invoice.status = InvoiceStatus.REVIEW_REQUIRED

        await db.flush()
        logger.info(
            "NEW_HIGH_RISK_SUPPLIER alert for invoice %s: supplier=%s, case=%s",
            invoice_id,
            supplier,
            "A" if most_recent is None else "B",
        )

        if invoice is not None:
            recipient_ids = [invoice.user_id]
            recipient_ids.extend(await get_finance_and_admin_user_ids(db))
            for uid in set(recipient_ids):
                await create_notification(
                    db,
                    user_id=uid,
                    title="Anomalie détectée",
                    message=alert.description,
                    notification_type="ANOMALY_ALERT",
                    related_invoice_id=invoice_id,
                )

    return alert


async def detect_price_spike(
    db: AsyncSession,
    invoice_id: UUID,
) -> AnomalyAlert | None:
    data_result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    current = data_result.scalar_one_or_none()
    if current is None or current.supplier_name is None or current.total_amount is None:
        return None

    supplier = current.supplier_name.strip()
    current_amount = float(current.total_amount)

    recent = await db.execute(
        select(InvoiceData.total_amount)
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.invoice_id != invoice_id,
            InvoiceData.supplier_name.isnot(None),
            func.trim(func.lower(InvoiceData.supplier_name)) == supplier.lower(),
            InvoiceData.total_amount.isnot(None),
            Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
        )
        .order_by(InvoiceData.invoice_date.desc())
        .limit(3)
    )
    amounts = [float(row[0]) for row in recent.all()]

    if len(amounts) < 1:
        return None

    avg_recent = float(np.mean(amounts))
    variation_pct = (current_amount - avg_recent) / avg_recent * 100

    spike_threshold = await get_threshold_value(db, "price_spike_pct", 30.0)
    if abs(variation_pct) <= spike_threshold:
        return None

    severity = Severity.HIGH if abs(variation_pct) > 60 else Severity.MEDIUM
    direction = "hausse" if variation_pct > 0 else "baisse"
    description = (
        f"{direction.capitalize()} de {abs(variation_pct):.1f}% par rapport à la moyenne "
        f"des {len(amounts)} dernière(s) facture(s) de {supplier} "
        f"({avg_recent:.2f} TND -> {current_amount} TND)"
    )

    alert = AnomalyAlert(
        invoice_id=invoice_id,
        alert_type=AlertType.PRICE_SPIKE,
        severity=severity,
        description=description,
        metric_value=round(float(variation_pct), 2),
        threshold_value=30.0,
        status=AlertStatus.PENDING,
    )
    db.add(alert)

    inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if invoice is not None:
        invoice.has_anomaly_alert = True
        if invoice.status != InvoiceStatus.REVIEW_REQUIRED:
            invoice.status = InvoiceStatus.REVIEW_REQUIRED

    await db.flush()
    logger.info(
        "PRICE_SPIKE alert for invoice %s: variation=%.2f%%, supplier=%s",
        invoice_id,
        variation_pct,
        supplier,
    )

    if invoice is not None:
        recipient_ids = [invoice.user_id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        for uid in set(recipient_ids):
            await create_notification(
                db,
                user_id=uid,
                title="Anomalie détectée",
                message=description,
                notification_type="ANOMALY_ALERT",
                related_invoice_id=invoice_id,
            )

    return alert


async def run_anomaly_detection(
    db: AsyncSession,
    invoice_id: UUID,
) -> dict[str, bool | int]:
    a1 = await detect_abnormal_amount(db, invoice_id)
    a2 = await detect_new_high_risk_supplier(db, invoice_id)
    a3 = await detect_price_spike(db, invoice_id)

    data_result = await db.execute(
        select(InvoiceData.supplier_name).where(InvoiceData.invoice_id == invoice_id)
    )
    supplier_name = data_result.scalar_one_or_none()
    if supplier_name is not None:
        await compute_supplier_risk_score(db, supplier_name.strip())

    results = {
        "abnormal_amount": a1 is not None,
        "new_high_risk_supplier": a2 is not None,
        "price_spike": a3 is not None,
    }
    results["total_alerts"] = sum(1 for v in results.values() if v)
    return results


async def compute_supplier_risk_score(
    db: AsyncSession,
    supplier_name: str,
) -> SupplierRiskScore:
    supplier = supplier_name.strip()
    today = date.today()

    invoices_query = await db.execute(
        select(
            func.count(InvoiceData.id),
            func.sum(InvoiceData.total_amount),
            func.avg(InvoiceData.total_amount),
            func.min(InvoiceData.invoice_date),
            func.max(InvoiceData.invoice_date),
        )
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.supplier_name.isnot(None),
            func.trim(func.lower(InvoiceData.supplier_name)) == supplier.lower(),
            InvoiceData.total_amount.isnot(None),
            Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
        )
    )
    row = invoices_query.one()
    total_invoices = int(row[0] or 0)
    total_amount_sum = float(row[1] or 0)
    avg_amount = float(row[2] or 0)
    first_seen_date = row[3]
    last_invoice_date = row[4]

    amounts_query = await db.execute(
        select(InvoiceData.total_amount)
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.supplier_name.isnot(None),
            func.trim(func.lower(InvoiceData.supplier_name)) == supplier.lower(),
            InvoiceData.total_amount.isnot(None),
            Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
        )
    )
    amounts = [float(r[0]) for r in amounts_query.all()]
    std_amount = float(np.std(amounts, ddof=0)) if len(amounts) > 0 else 0.0

    anomaly_count_result = await db.execute(
        select(func.count(AnomalyAlert.id))
        .join(Invoice, AnomalyAlert.invoice_id == Invoice.id)
        .join(InvoiceData, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.supplier_name.isnot(None),
            func.trim(func.lower(InvoiceData.supplier_name)) == supplier.lower(),
        )
    )
    anomaly_count = int(anomaly_count_result.scalar() or 0)

    anomaly_ratio_score = min(100, (anomaly_count / max(total_invoices, 1)) * 100 * 2)
    volatility_score = min(100, (std_amount / max(avg_amount, 1)) * 100)

    if last_invoice_date is not None:
        days_since_last = (today - last_invoice_date).days
        recency_score = min(100, max(0, (days_since_last - 30) / 1.5))
    else:
        recency_score = 0.0

    risk_score = round(anomaly_ratio_score * 0.5 + volatility_score * 0.3 + recency_score * 0.2)
    risk_score = max(0, min(100, risk_score))

    existing = await db.execute(
        select(SupplierRiskScore).where(
            func.lower(SupplierRiskScore.supplier_name) == supplier.lower()
        )
    )
    score_row = existing.scalar_one_or_none()

    if score_row is None:
        score_row = SupplierRiskScore(
            supplier_name=supplier,
            risk_score=risk_score,
            total_invoices=total_invoices,
            total_amount_sum=total_amount_sum,
            avg_amount=avg_amount,
            std_amount=std_amount,
            anomaly_count=anomaly_count,
            last_invoice_date=last_invoice_date,
            first_seen_date=first_seen_date,
        )
        db.add(score_row)
    else:
        score_row.risk_score = risk_score
        score_row.total_invoices = total_invoices
        score_row.total_amount_sum = total_amount_sum
        score_row.avg_amount = avg_amount
        score_row.std_amount = std_amount
        score_row.anomaly_count = anomaly_count
        score_row.last_invoice_date = last_invoice_date
        score_row.first_seen_date = first_seen_date
        score_row.updated_at = datetime.now(timezone.utc)

    await db.flush()
    logger.info(
        "Supplier risk score computed for %s: score=%d, invoices=%d, anomalies=%d",
        supplier,
        risk_score,
        total_invoices,
        anomaly_count,
    )
    return score_row


async def recompute_all_supplier_risk_scores(
    db: AsyncSession,
) -> int:
    distinct_result = await db.execute(
        select(func.distinct(func.trim(func.lower(InvoiceData.supplier_name))))
        .join(Invoice, InvoiceData.invoice_id == Invoice.id)
        .where(
            InvoiceData.supplier_name.isnot(None),
            Invoice.status.in_([InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED]),
        )
    )
    supplier_names = set()
    for row in distinct_result.all():
        raw = row[0]
        if raw:
            supplier_names.add(raw)

    for name in supplier_names:
        await compute_supplier_risk_score(db, name)

    logger.info("Recomputed risk scores for %d suppliers", len(supplier_names))
    return len(supplier_names)


async def get_anomaly_alerts(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> list[AnomalyAlertResponse]:
    result = await db.execute(
        select(AnomalyAlert).where(AnomalyAlert.invoice_id == invoice_id)
    )
    alerts = result.scalars().all()

    if current_user.role not in (UserRole.ADMIN, UserRole.FINANCE):
        inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = inv_result.scalar_one_or_none()
        if invoice is None or invoice.user_id != current_user.id:
            return []

    return [await _alert_to_response(db, a) for a in alerts]


async def acknowledge_anomaly_alert(
    db: AsyncSession,
    alert_id: UUID,
    action: AnomalyAcknowledgeRequest,
    current_user: User,
) -> AnomalyAlertResponse:
    result = await db.execute(select(AnomalyAlert).where(AnomalyAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.status = AlertStatus(action.status)
    alert.acknowledged_by_user_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)

    pending_alerts = await db.execute(
        select(func.count()).select_from(AnomalyAlert).where(
            AnomalyAlert.invoice_id == alert.invoice_id,
            AnomalyAlert.status == AlertStatus.PENDING,
        )
    )
    pending_alert_count = pending_alerts.scalar() or 0

    if pending_alert_count == 0:
        pending_dups = await db.execute(
            select(func.count()).select_from(DuplicateMatch).where(
                or_(
                    DuplicateMatch.invoice_id == alert.invoice_id,
                    DuplicateMatch.matched_invoice_id == alert.invoice_id,
                ),
                DuplicateMatch.status == DuplicateStatus.PENDING,
            )
        )
        pending_dup_count = pending_dups.scalar() or 0

        if pending_dup_count == 0:
            inv_result = await db.execute(
                select(Invoice).where(Invoice.id == alert.invoice_id)
            )
            invoice = inv_result.scalar_one_or_none()
            if invoice is not None and invoice.status == InvoiceStatus.REVIEW_REQUIRED:
                data_result = await db.execute(
                    select(InvoiceData).where(InvoiceData.invoice_id == alert.invoice_id)
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
    return await _alert_to_response(db, alert)


async def get_pending_anomalies(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    alert_type: AlertType | None = None,
    severity: Severity | None = None,
) -> tuple[list[AnomalyAlertResponse], int, int]:
    conditions = [AnomalyAlert.status == AlertStatus.PENDING]

    if current_user.role not in (UserRole.ADMIN, UserRole.FINANCE):
        conditions.append(
            AnomalyAlert.invoice_id.in_(
                select(Invoice.id).where(Invoice.user_id == current_user.id)
            )
        )

    if alert_type is not None:
        conditions.append(AnomalyAlert.alert_type == alert_type)

    if severity is not None:
        conditions.append(AnomalyAlert.severity == severity)

    total_result = await db.execute(
        select(func.count()).select_from(AnomalyAlert).where(*conditions)
    )
    total = total_result.scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    severity_order = case(
        (AnomalyAlert.severity == Severity.HIGH, 0),
        (AnomalyAlert.severity == Severity.MEDIUM, 1),
        else_=2,
    )

    alerts_result = await db.execute(
        select(AnomalyAlert)
        .where(*conditions)
        .order_by(severity_order, AnomalyAlert.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    alerts = alerts_result.scalars().all()

    responses = [await _alert_to_response(db, a) for a in alerts]
    return responses, total, total_pages


async def get_supplier_risk_scores(
    db: AsyncSession,
    current_user: User,
    min_risk_score: int | None = None,
) -> list[SupplierRiskScore]:
    conditions: list = []

    if min_risk_score is not None:
        conditions.append(SupplierRiskScore.risk_score >= min_risk_score)

    result = await db.execute(
        select(SupplierRiskScore)
        .where(*conditions)
        .order_by(SupplierRiskScore.risk_score.desc())
    )
    return list(result.scalars().all())


async def _alert_to_response(
    db: AsyncSession,
    alert: AnomalyAlert,
) -> AnomalyAlertResponse:
    inv_result = await db.execute(select(Invoice).where(Invoice.id == alert.invoice_id))
    invoice = inv_result.scalar_one_or_none()

    summary = InvoiceSummary(
        id=alert.invoice_id,
        original_filename=invoice.original_filename if invoice else "",
    )
    if invoice is not None:
        data_result = await db.execute(
            select(InvoiceData).where(InvoiceData.invoice_id == invoice.id)
        )
        data = data_result.scalar_one_or_none()
        if data is not None:
            summary.invoice_number = data.invoice_number
            summary.supplier_name = data.supplier_name
            summary.total_amount = float(data.total_amount) if data.total_amount else None
            summary.invoice_date = data.invoice_date

    return AnomalyAlertResponse(
        id=alert.id,
        invoice_id=alert.invoice_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        description=alert.description,
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        status=alert.status,
        acknowledged_by_user_id=alert.acknowledged_by_user_id,
        acknowledged_at=alert.acknowledged_at,
        created_at=alert.created_at,
        invoice=summary,
    )
