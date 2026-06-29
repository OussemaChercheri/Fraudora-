import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly_alert import AlertStatus, AlertType, AnomalyAlert, Severity
from app.models.duplicate_match import DuplicateMatch, DuplicateStatus, MatchType
from app.models.invoice import FileType, Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.models.user import User, UserRole
from app.services.anomaly_service import compute_supplier_risk_score
from app.services.notification_service import create_notification, get_finance_and_admin_user_ids
from app.utils.security import hash_password

SUPPLIERS = [
    "STEG",
    "SONEDE",
    "Ooredoo TN",
    "Tunisie Telecom",
    "TRANSTU",
    "Poulina Group",
    "Délice Danone",
]

FILE_TYPES = [FileType.PDF, FileType.PDF, FileType.PDF, FileType.JPG, FileType.PNG]

DEMO_INVOICE_PREFIXES = [
    "facture_{supplier}_{month}.pdf",
    "invoice_{supplier}_2026.pdf",
    "facture_{supplier}_TND.pdf",
    "scan_facture_{supplier}.jpg",
    "facture_{supplier}_mars2026.png",
]


async def _upsert_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
    else:
        user.full_name = full_name
        user.hashed_password = hash_password(password)
        user.role = role
        user.is_active = True
    await db.flush()
    return user


def _random_invoice_date() -> date:
    days_ago = random.randint(0, 180)
    return date.today() - timedelta(days=days_ago)


def _demo_filename(supplier: str) -> str:
    template = random.choice(DEMO_INVOICE_PREFIXES)
    month = random.choice(
        ["janvier", "fevrier", "mars", "avril", "mai", "juin"]
    )
    supplier_slug = supplier.lower().replace(" ", "_")
    return template.format(supplier=supplier_slug, month=month)


def _build_invoice_data(
    *,
    status: InvoiceStatus,
    supplier: str,
    total_amount: Decimal,
    tax_amount: Decimal,
    invoice_number: str,
    invoice_date: date,
) -> InvoiceData | None:
    if status == InvoiceStatus.UPLOADED:
        return None

    if status == InvoiceStatus.ERROR:
        return None

    if status == InvoiceStatus.PROCESSED:
        return InvoiceData(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            supplier_name=supplier,
            total_amount=total_amount,
            tax_amount=tax_amount,
            confidence_invoice_number=round(random.uniform(0.75, 1.0), 4),
            confidence_invoice_date=round(random.uniform(0.75, 1.0), 4),
            confidence_supplier_name=round(random.uniform(0.75, 1.0), 4),
            confidence_total_amount=round(random.uniform(0.75, 1.0), 4),
            confidence_tax_amount=round(random.uniform(0.75, 1.0), 4),
        )

    fields = {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "supplier_name": supplier,
        "total_amount": total_amount,
        "tax_amount": tax_amount,
    }
    nullable_keys = random.sample(
        list(fields.keys()),
        k=random.randint(1, 2),
    )
    for key in nullable_keys:
        fields[key] = None

    return InvoiceData(
        invoice_number=fields["invoice_number"],
        invoice_date=fields["invoice_date"],
        supplier_name=fields["supplier_name"],
        total_amount=fields["total_amount"],
        tax_amount=fields["tax_amount"],
        confidence_invoice_number=round(random.uniform(0.2, 0.6), 4),
        confidence_invoice_date=round(random.uniform(0.2, 0.6), 4),
        confidence_supplier_name=round(random.uniform(0.2, 0.6), 4),
        confidence_total_amount=round(random.uniform(0.2, 0.6), 4),
        confidence_tax_amount=round(random.uniform(0.2, 0.6), 4),
    )


async def seed_demo(db: AsyncSession) -> None:
    await _upsert_user(
        db,
        email="admin@fraudguard.tn",
        password="Admin@2026",
        full_name="Admin FraudGuard",
        role=UserRole.ADMIN,
    )

    comptable = await _upsert_user(
        db,
        email="comptable@demo-client.tn",
        password="Demo@2026",
        full_name="Mohamed Ben Ali",
        role=UserRole.COMPTABLE,
    )

    await _upsert_user(
        db,
        email="finance@fraudguard.tn",
        password="Finance@2026",
        full_name="Leila Finance",
        role=UserRole.FINANCE,
    )

    await _upsert_user(
        db,
        email="viewer@fraudguard.tn",
        password="Viewer@2026",
        full_name="Visitor View",
        role=UserRole.VIEWER,
    )

    await db.execute(delete(Invoice).where(Invoice.user_id == comptable.id))

    statuses = (
        [InvoiceStatus.PROCESSED] * 8
        + [InvoiceStatus.REVIEW_REQUIRED] * 4
        + [InvoiceStatus.ERROR] * 2
        + [InvoiceStatus.UPLOADED] * 1
    )
    random.shuffle(statuses)

    now = datetime.now(timezone.utc)

    for status in statuses:
        supplier = random.choice(SUPPLIERS)
        total_amount = Decimal(str(round(random.uniform(150.0, 12000.0), 3)))
        tax_amount = (total_amount * Decimal("0.19")).quantize(Decimal("0.001"))
        invoice_number = f"FA-2026-{random.randint(1000, 9999)}"
        invoice_date = _random_invoice_date()
        file_type = random.choice(FILE_TYPES)
        stored_name = f"{uuid.uuid4()}.{file_type.value.lower()}"
        original_filename = _demo_filename(supplier)

        invoice = Invoice(
            user_id=comptable.id,
            original_filename=original_filename,
            stored_filename=stored_name,
            file_path=f"./uploads/demo/{stored_name}",
            file_type=file_type,
            file_size_kb=random.randint(120, 2400),
            status=status,
            created_at=now - timedelta(days=random.randint(0, 180)),
            updated_at=now,
        )

        if status == InvoiceStatus.ERROR:
            invoice.error_message = "Tesseract: unreadable scan quality"
        elif status in (InvoiceStatus.PROCESSED, InvoiceStatus.REVIEW_REQUIRED):
            invoice.ocr_page_count = random.randint(1, 3)
            invoice.ocr_processing_time_ms = random.randint(2000, 15000)
            invoice.ocr_raw_text = (
                f"FACTURE\n{supplier}\nN° {invoice_number}\n"
                f"Date: {invoice_date.isoformat()}\n"
                f"Total TTC: {total_amount} TND\nTVA: {tax_amount} TND"
            )

        invoice_data = _build_invoice_data(
            status=status,
            supplier=supplier,
            total_amount=total_amount,
            tax_amount=tax_amount,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
        )
        if invoice_data is not None:
            invoice.invoice_data = invoice_data

        db.add(invoice)

    await db.flush()

    # ── Create duplicate scenarios for demo/testing ──
    processed_result = await db.execute(
        select(Invoice)
        .where(
            Invoice.user_id == comptable.id,
            Invoice.status == InvoiceStatus.PROCESSED,
        )
        .order_by(Invoice.created_at.desc())
        .limit(4)
    )
    targets = processed_result.scalars().all()

    if len(targets) >= 4:
        now = datetime.now(timezone.utc)

        fuzzy_variants = {
            "STEG": "STEG Tunisie",
            "SONEDE": "SONEDE Tunisie",
            "Ooredoo TN": "Ooredoo Tunisie",
            "Tunisie Telecom": "Tunisie Telecom Mobile",
            "TRANSTU": "TRANSTU SA",
            "Poulina Group": "Groupe Poulina",
            "Délice Danone": "Danone Delice",
        }

        for idx, target in enumerate(targets):
            data_result = await db.execute(
                select(InvoiceData).where(InvoiceData.invoice_id == target.id)
            )
            target_data = data_result.scalar_one_or_none()
            if target_data is None or not target_data.invoice_number:
                continue

            is_exact = idx < 2

            orig_amount = target_data.total_amount or Decimal("1000.00")
            variation = Decimal("0.03") if is_exact else Decimal(str(round(random.uniform(-0.05, 0.05), 3)))
            dup_amount = (orig_amount * (Decimal("1") + variation)).quantize(Decimal("0.001"))

            supplier_name = (
                target_data.supplier_name
                if is_exact
                else fuzzy_variants.get(target_data.supplier_name or "", target_data.supplier_name or "STEG")
            )

            invoice_date = target_data.invoice_date or _random_invoice_date()
            dup_date = invoice_date if is_exact else invoice_date + timedelta(days=random.randint(-3, 3))

            inv_number = target_data.invoice_number if is_exact else f"FA-2026-{random.randint(1000, 9999)}"
            raw_text = (
                f"FACTURE (doublon)\n{supplier_name}\n"
                f"N° {inv_number}\n"
                f"Date: {dup_date.isoformat()}\n"
                f"Total TTC: {dup_amount} TND"
            )

            dup_invoice = Invoice(
                user_id=comptable.id,
                original_filename=f"{'exact' if is_exact else 'fuzzy'}_{idx}_{target.original_filename}",
                stored_filename=f"{uuid.uuid4()}.{target.file_type.value.lower()}",
                file_path="./uploads/demo/duplicate",
                file_type=target.file_type,
                file_size_kb=random.randint(120, 2400),
                status=InvoiceStatus.REVIEW_REQUIRED,
                has_duplicate_alert=True,
                created_at=now - timedelta(hours=random.randint(1, 12)),
                updated_at=now,
                ocr_page_count=random.randint(1, 3),
                ocr_processing_time_ms=random.randint(2000, 15000),
                ocr_raw_text=raw_text,
            )
            db.add(dup_invoice)
            await db.flush()

            dup_data = InvoiceData(
                invoice_id=dup_invoice.id,
                invoice_number=inv_number,
                invoice_date=dup_date,
                supplier_name=supplier_name,
                total_amount=dup_amount,
                tax_amount=(dup_amount * Decimal("0.19")).quantize(Decimal("0.001")),
                confidence_invoice_number=0.95 if is_exact else 0.85,
                confidence_invoice_date=0.85 if is_exact else 0.80,
                confidence_supplier_name=0.90 if is_exact else 0.75,
                confidence_total_amount=0.80 if is_exact else 0.85,
                confidence_tax_amount=0.75 if is_exact else 0.70,
            )
            db.add(dup_data)
            await db.flush()

            existing = await db.execute(
                select(DuplicateMatch).where(
                    DuplicateMatch.invoice_id == dup_invoice.id,
                    DuplicateMatch.matched_invoice_id == target.id,
                )
            )
            if existing.scalar_one_or_none() is None:
                match = DuplicateMatch(
                    invoice_id=dup_invoice.id,
                    matched_invoice_id=target.id,
                    match_type=MatchType.EXACT_NUMBER if is_exact else MatchType.FUZZY_SIMILARITY,
                    similarity_score=100.0 if is_exact else round(random.uniform(85.0, 95.0), 2),
                    status=DuplicateStatus.PENDING,
                )
                db.add(match)

                recipient_ids = [comptable.id]
                recipient_ids.extend(await get_finance_and_admin_user_ids(db))
                for uid in set(recipient_ids):
                    await create_notification(
                        db,
                        user_id=uid,
                        title="Doublon potentiel détecté",
                        message=(
                            f"La facture {dup_invoice.original_filename} ressemble à "
                            f"une facture existante ({match.similarity_score}%)"
                        ),
                        notification_type="DUPLICATE_ALERT",
                        related_invoice_id=dup_invoice.id,
                    )

    await db.flush()
    # ── Create anomaly scenarios for demo/testing ──
    existing_alert_count = await db.execute(
        select(func.count()).select_from(AnomalyAlert)
    )
    if existing_alert_count.scalar() == 0:
        now = datetime.now(timezone.utc)
        today = date.today()

        # ── 1. ABNORMAL_AMOUNT: Ooredoo TN (3 normal ~200-400 TND, 1 anomalous 2500 TND) ──
        ooredoo_normal = [(Decimal("250.000"), -60), (Decimal("320.000"), -40), (Decimal("380.000"), -20)]
        for i, (amt, days_offset) in enumerate(ooredoo_normal):
            inv = Invoice(
                user_id=comptable.id,
                original_filename=f"ooredoo_normal_{i}.pdf",
                stored_filename=f"{uuid.uuid4()}.pdf",
                file_path="./uploads/demo/",
                file_type=FileType.PDF,
                file_size_kb=random.randint(120, 2400),
                status=InvoiceStatus.PROCESSED,
                created_at=now + timedelta(days=days_offset),
                updated_at=now,
                ocr_page_count=1,
                ocr_processing_time_ms=random.randint(2000, 15000),
                ocr_raw_text=f"FACTURE\nOoredoo TN\nN° FA-2026-{9000 + i}\nTotal TTC: {amt} TND",
            )
            db.add(inv)
            await db.flush()
            db.add(InvoiceData(
                invoice_id=inv.id,
                invoice_number=f"FA-2026-{9000 + i}",
                invoice_date=today + timedelta(days=days_offset),
                supplier_name="Ooredoo TN",
                total_amount=amt,
                tax_amount=(amt * Decimal("0.19")).quantize(Decimal("0.001")),
                confidence_invoice_number=0.95,
                confidence_invoice_date=0.90,
                confidence_supplier_name=0.95,
                confidence_total_amount=0.90,
                confidence_tax_amount=0.85,
            ))
            await db.flush()

        ooredoo_anomaly_inv = Invoice(
            user_id=comptable.id,
            original_filename="facture_ooredoo_anomal.pdf",
            stored_filename=f"{uuid.uuid4()}.pdf",
            file_path="./uploads/demo/",
            file_type=FileType.PDF,
            file_size_kb=random.randint(120, 2400),
            status=InvoiceStatus.REVIEW_REQUIRED,
            has_anomaly_alert=True,
            created_at=now,
            updated_at=now,
            ocr_page_count=1,
            ocr_processing_time_ms=random.randint(2000, 15000),
            ocr_raw_text="FACTURE\nOoredoo TN\nN° FA-ANOMAL-001\nTotal TTC: 2500 TND",
        )
        db.add(ooredoo_anomaly_inv)
        await db.flush()
        anomaly_amount = Decimal("2500.000")
        db.add(InvoiceData(
            invoice_id=ooredoo_anomaly_inv.id,
            invoice_number="FA-ANOMAL-001",
            invoice_date=today,
            supplier_name="Ooredoo TN",
            total_amount=anomaly_amount,
            tax_amount=(anomaly_amount * Decimal("0.19")).quantize(Decimal("0.001")),
            confidence_invoice_number=0.95,
            confidence_invoice_date=0.90,
            confidence_supplier_name=0.95,
            confidence_total_amount=0.95,
            confidence_tax_amount=0.85,
        ))
        await db.flush()
        db.add(AnomalyAlert(
            invoice_id=ooredoo_anomaly_inv.id,
            alert_type=AlertType.ABNORMAL_AMOUNT,
            severity=Severity.HIGH,
            description=(
                f"Montant de 2500.0 TND dépasse la moyenne habituelle de 316.67 TND "
                f"pour Ooredoo TN (seuil: moyenne + 2 écarts-types = 410.29 TND)"
            ),
            metric_value=46.6,
            threshold_value=410.29,
            status=AlertStatus.PENDING,
        ))

        recipient_ids = [comptable.id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        for uid in set(recipient_ids):
            await create_notification(
                db,
                user_id=uid,
                title="Anomalie détectée",
                message="Montant de 2500.0 TND dépasse la moyenne habituelle de 316.67 TND pour Ooredoo TN",
                notification_type="ANOMALY_ALERT",
                related_invoice_id=ooredoo_anomaly_inv.id,
            )

        # ── 2. NEW_HIGH_RISK_SUPPLIER: Nouvelle Entreprise XYZ ──
        new_supplier_inv = Invoice(
            user_id=comptable.id,
            original_filename="facture_nouveau_fournisseur.pdf",
            stored_filename=f"{uuid.uuid4()}.pdf",
            file_path="./uploads/demo/",
            file_type=FileType.PDF,
            file_size_kb=random.randint(120, 2400),
            status=InvoiceStatus.REVIEW_REQUIRED,
            has_anomaly_alert=True,
            created_at=now,
            updated_at=now,
            ocr_page_count=1,
            ocr_processing_time_ms=random.randint(2000, 15000),
            ocr_raw_text="FACTURE\nNouvelle Entreprise XYZ\nN° FA-XYZ-001\nTotal TTC: 1500 TND",
        )
        db.add(new_supplier_inv)
        await db.flush()
        new_sup_amount = Decimal("1500.000")
        db.add(InvoiceData(
            invoice_id=new_supplier_inv.id,
            invoice_number="FA-XYZ-001",
            invoice_date=today,
            supplier_name="Nouvelle Entreprise XYZ",
            total_amount=new_sup_amount,
            tax_amount=(new_sup_amount * Decimal("0.19")).quantize(Decimal("0.001")),
            confidence_invoice_number=0.90,
            confidence_invoice_date=0.85,
            confidence_supplier_name=0.95,
            confidence_total_amount=0.90,
            confidence_tax_amount=0.80,
        ))
        await db.flush()
        db.add(AnomalyAlert(
            invoice_id=new_supplier_inv.id,
            alert_type=AlertType.NEW_HIGH_RISK_SUPPLIER,
            severity=Severity.MEDIUM,
            description=(
                "Nouveau fournisseur détecté : 'Nouvelle Entreprise XYZ' "
                "n'a jamais été référencé auparavant. Vérification recommandée."
            ),
            metric_value=0,
            threshold_value=0,
            status=AlertStatus.PENDING,
        ))

        recipient_ids = [comptable.id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        for uid in set(recipient_ids):
            await create_notification(
                db,
                user_id=uid,
                title="Anomalie détectée",
                message="Nouveau fournisseur détecté : 'Nouvelle Entreprise XYZ' n'a jamais été référencé",
                notification_type="ANOMALY_ALERT",
                related_invoice_id=new_supplier_inv.id,
            )

        # ── 3. PRICE_SPIKE: Poulina Group (2 normal ~500 TND, 1 spike 850 TND) ──
        poulina_normal = [(Decimal("500.000"), -30), (Decimal("500.000"), -15)]
        for i, (amt, days_offset) in enumerate(poulina_normal):
            inv = Invoice(
                user_id=comptable.id,
                original_filename=f"poulina_normal_{i}.pdf",
                stored_filename=f"{uuid.uuid4()}.pdf",
                file_path="./uploads/demo/",
                file_type=FileType.PDF,
                file_size_kb=random.randint(120, 2400),
                status=InvoiceStatus.PROCESSED,
                created_at=now + timedelta(days=days_offset),
                updated_at=now,
                ocr_page_count=1,
                ocr_processing_time_ms=random.randint(2000, 15000),
                ocr_raw_text=f"FACTURE\nPoulina Group\nN° FA-2026-{8000 + i}\nTotal TTC: {amt} TND",
            )
            db.add(inv)
            await db.flush()
            db.add(InvoiceData(
                invoice_id=inv.id,
                invoice_number=f"FA-2026-{8000 + i}",
                invoice_date=today + timedelta(days=days_offset),
                supplier_name="Poulina Group",
                total_amount=amt,
                tax_amount=(amt * Decimal("0.19")).quantize(Decimal("0.001")),
                confidence_invoice_number=0.95,
                confidence_invoice_date=0.90,
                confidence_supplier_name=0.95,
                confidence_total_amount=0.90,
                confidence_tax_amount=0.85,
            ))
            await db.flush()

        spike_inv = Invoice(
            user_id=comptable.id,
            original_filename="facture_poulina_spike.pdf",
            stored_filename=f"{uuid.uuid4()}.pdf",
            file_path="./uploads/demo/",
            file_type=FileType.PDF,
            file_size_kb=random.randint(120, 2400),
            status=InvoiceStatus.REVIEW_REQUIRED,
            has_anomaly_alert=True,
            created_at=now,
            updated_at=now,
            ocr_page_count=1,
            ocr_processing_time_ms=random.randint(2000, 15000),
            ocr_raw_text="FACTURE\nPoulina Group\nN° FA-SPIKE-001\nTotal TTC: 850 TND",
        )
        db.add(spike_inv)
        await db.flush()
        spike_amount = Decimal("850.000")
        db.add(InvoiceData(
            invoice_id=spike_inv.id,
            invoice_number="FA-SPIKE-001",
            invoice_date=today,
            supplier_name="Poulina Group",
            total_amount=spike_amount,
            tax_amount=(spike_amount * Decimal("0.19")).quantize(Decimal("0.001")),
            confidence_invoice_number=0.95,
            confidence_invoice_date=0.90,
            confidence_supplier_name=0.95,
            confidence_total_amount=0.95,
            confidence_tax_amount=0.85,
        ))
        await db.flush()
        db.add(AnomalyAlert(
            invoice_id=spike_inv.id,
            alert_type=AlertType.PRICE_SPIKE,
            severity=Severity.HIGH,
            description=(
                f"Hausse de 70.0% par rapport à la moyenne des 2 dernière(s) facture(s) de "
                f"Poulina Group (500.00 TND -> 850 TND)"
            ),
            metric_value=70.0,
            threshold_value=30.0,
            status=AlertStatus.PENDING,
        ))

        recipient_ids = [comptable.id]
        recipient_ids.extend(await get_finance_and_admin_user_ids(db))
        for uid in set(recipient_ids):
            await create_notification(
                db,
                user_id=uid,
                title="Anomalie détectée",
                message="Hausse de 70.0% par rapport à la moyenne des factures de Poulina Group (500 TND -> 850 TND)",
                notification_type="ANOMALY_ALERT",
                related_invoice_id=spike_inv.id,
            )

        await db.flush()
        # ── 4. Compute risk scores for affected suppliers ──
        for name in ("Ooredoo TN", "Nouvelle Entreprise XYZ", "Poulina Group"):
            await compute_supplier_risk_score(db, name)

    await db.commit()
