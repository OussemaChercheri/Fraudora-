import logging
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.anomaly_alert import AlertStatus, AnomalyAlert, Severity
from app.models.duplicate_match import DuplicateMatch, DuplicateStatus
from app.models.notification import Notification
from app.models.supplier_risk_score import SupplierRiskScore
from app.models.user import User, UserRole
from app.services.threshold_service import get_threshold_value

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body_html: str) -> bool:
    settings = get_settings()
    if not settings.SMTP_ENABLED:
        logger.info(
            "[EMAIL-DEV] To: %s | Subject: %s\n%s",
            to,
            subject,
            body_html,
        )
        return True

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


async def build_daily_summary_html(db: AsyncSession, user: User) -> str:
    today = date.today()
    yesterday = today - timedelta(days=1)

    notif_result = await db.execute(
        select(Notification.notification_type, func.count())
        .where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
            func.date(Notification.created_at) >= yesterday,
        )
        .group_by(Notification.notification_type)
    )
    notif_rows = notif_result.all()

    dup_result = await db.execute(
        select(func.count()).select_from(DuplicateMatch).where(
            DuplicateMatch.status == DuplicateStatus.PENDING,
        )
    )
    dup_count = dup_result.scalar() or 0

    sev_result = await db.execute(
        select(AnomalyAlert.severity, func.count())
        .where(AnomalyAlert.status == AlertStatus.PENDING)
        .group_by(AnomalyAlert.severity)
    )
    sev_rows = sev_result.all()

    top_suppliers_result = await db.execute(
        select(SupplierRiskScore)
        .order_by(SupplierRiskScore.risk_score.desc())
        .limit(3)
    )
    top_suppliers = list(top_suppliers_result.scalars().all())

    date_str = today.strftime("%d/%m/%Y")
    html_parts = [f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px;">
<div style="max-width: 600px; margin: auto; background: #fff; border-radius: 8px; padding: 24px;">
<h1 style="color: #1a237e; font-size: 20px; margin: 0 0 16px 0;">
  Résumé quotidien FraudGuard AI — {date_str}
</h1>
<p style="color: #555; font-size: 14px;">Bonjour <strong>{user.full_name}</strong>, voici le récapitulatif du jour.</p>
"""]

    if notif_rows:
        html_parts.append("""<h2 style="font-size: 16px; color: #333; margin: 20px 0 8px 0;">Notifications non lues</h2>""")
        html_parts.append("""<table style="width:100%; border-collapse: collapse; font-size: 13px;">""")
        html_parts.append("""<tr style="background: #e8eaf6;"><th style="text-align:left;padding:8px;">Type</th><th style="text-align:left;padding:8px;">Nombre</th></tr>""")
        for ntype, count in notif_rows:
            html_parts.append(f"""<tr><td style="padding:6px 8px;border-bottom:1px solid #ddd;">{ntype.value}</td><td style="padding:6px 8px;border-bottom:1px solid #ddd;">{count}</td></tr>""")
        html_parts.append("</table>")

    html_parts.append(f"""<h2 style="font-size: 16px; color: #333; margin: 20px 0 8px 0;">Doublons en attente</h2>""")
    html_parts.append(f"""<p style="font-size: 14px; margin: 0;">{dup_count} doublon(s) à vérifier.</p>""")

    html_parts.append("""<h2 style="font-size: 16px; color: #333; margin: 20px 0 8px 0;">Anomalies en attente</h2>""")
    if sev_rows:
        html_parts.append("""<table style="width:100%; border-collapse: collapse; font-size: 13px;">""")
        html_parts.append("""<tr style="background: #e8eaf6;"><th style="text-align:left;padding:8px;">Sévérité</th><th style="text-align:left;padding:8px;">Nombre</th></tr>""")
        sev_total = 0
        for sev, count in sev_rows:
            sev_total += count
            html_parts.append(f"""<tr><td style="padding:6px 8px;border-bottom:1px solid #ddd;">{sev.value}</td><td style="padding:6px 8px;border-bottom:1px solid #ddd;">{count}</td></tr>""")
        html_parts.append(f"""<tr style="font-weight:bold;"><td style="padding:6px 8px;">Total</td><td style="padding:6px 8px;">{sev_total}</td></tr>""")
        html_parts.append("</table>")
    else:
        html_parts.append("""<p style="font-size: 14px; margin: 0;">Aucune anomalie en attente.</p>""")

    html_parts.append("""<h2 style="font-size: 16px; color: #333; margin: 20px 0 8px 0;">Fournisseurs les plus risqués</h2>""")
    if top_suppliers:
        html_parts.append("""<table style="width:100%; border-collapse: collapse; font-size: 13px;">""")
        html_parts.append("""<tr style="background: #e8eaf6;"><th style="text-align:left;padding:8px;">Fournisseur</th><th style="text-align:left;padding:8px;">Score</th></tr>""")
        for s in top_suppliers:
            html_parts.append(f"""<tr><td style="padding:6px 8px;border-bottom:1px solid #ddd;">{s.supplier_name}</td><td style="padding:6px 8px;border-bottom:1px solid #ddd;">{s.risk_score}</td></tr>""")
        html_parts.append("</table>")
    else:
        html_parts.append("""<p style="font-size: 14px; margin: 0;">Aucun fournisseur évalué.</p>""")

    html_parts.append("""
<hr style="border: none; border-top: 1px solid #eee; margin: 24px 0 12px 0;">
<p style="font-size: 11px; color: #999;">Ce message est généré automatiquement par FraudGuard AI. Merci de ne pas y répondre.</p>
</div></body></html>""")

    return "\n".join(html_parts)


async def send_daily_summaries(db: AsyncSession) -> int:
    enabled = await get_threshold_value(db, "daily_email_enabled", 1.0)
    if enabled == 0:
        logger.info("Daily email disabled via threshold (daily_email_enabled=0)")
        return 0

    result = await db.execute(
        select(User).where(
            User.role.in_([UserRole.FINANCE, UserRole.ADMIN]),
            User.is_active.is_(True),
        )
    )
    users = list(result.scalars().all())

    settings = get_settings()
    sent = 0
    for user in users:
        html = await build_daily_summary_html(db, user)
        ok = send_email(user.email, f"FraudGuard AI — Résumé quotidien {date.today()}", html)
        if ok:
            sent += 1
    logger.info("Daily summaries sent to %d/%d users", sent, len(users))
    return sent
