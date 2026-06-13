import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_threshold import AlertThreshold

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS: list[tuple[str, float, str]] = [
    ("abnormal_amount_zscore", 2.0, "Seuil z-score pour montant anormal (US-16)"),
    ("dormant_supplier_days", 180.0, "Nombre de jours d'inactivité avant alerte fournisseur dormant (US-17)"),
    ("price_spike_pct", 30.0, "Pourcentage de variation de prix déclenchant une alerte (US-18)"),
    ("fuzzy_duplicate_similarity", 85.0, "Seuil de similarité pour doublon flou en % (US-14)"),
    ("daily_email_enabled", 1.0, "Activer l'envoi de l'email récapitulatif quotidien (1=oui, 0=non)"),
]


async def seed_default_thresholds(db: AsyncSession) -> None:
    for key, value, description in DEFAULT_THRESHOLDS:
        existing = await db.execute(
            select(AlertThreshold).where(AlertThreshold.threshold_key == key)
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                AlertThreshold(
                    threshold_key=key,
                    threshold_value=value,
                    description=description,
                )
            )
            logger.info("Seeded threshold: %s = %s", key, value)
    await db.commit()
