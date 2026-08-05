"""Parcours d'intégration Life Pilot sur PostgreSQL réel."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text

from app.core.security import get_password_hash
from app.services.categorization_service import CategorizationService

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
PASSWORD = "Correct-Horse-2026!"

pytestmark = pytest.mark.asyncio


async def test_parcours_integration_utilisateur_finance_documents(client, db_session):
    """Couvre auth, comptes, imports, catégories, documents, rappels et dashboard."""

    # 1. Création utilisateur via SQL, équivalent persistance du futur endpoint signup.
    result = await db_session.execute(
        text(
            """
            INSERT INTO users (email, password_hash, display_name)
            VALUES (:email, :password_hash, :display_name)
            RETURNING id, email
            """
        ),
        {
            "email": "integration@example.com",
            "password_hash": get_password_hash(PASSWORD),
            "display_name": "Integration Test",
        },
    )
    user = result.mappings().one()
    await db_session.execute(
        text(
            """
            INSERT INTO categories (user_id, parent_id, name, type, is_system)
            SELECT :user_id, NULL, template.name, template.type, true
            FROM categories AS template
            WHERE template.user_id IS NULL AND template.is_system = true
            """
        ),
        {"user_id": user.id},
    )
    await db_session.commit()
    assert user.email == "integration@example.com"

    # 2. Connexion et vérification du profil authentifié.
    login = await client.post(
        "/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == user.email

    # 3. Création d'un compte manuel.
    account_response = await client.post(
        "/accounts/manual",
        headers=headers,
        json={
            "provider": "manual",
            "account_type": "checking",
            "name": "Compte courant test",
            "iban": "FR7612345678901234567890185",
            "currency": "EUR",
            "balance_current": "1200.00",
        },
    )
    assert account_response.status_code == 201, account_response.text
    account_id = account_response.json()["id"]

    category_rows = await db_session.execute(
        text(
            """
            SELECT id, name FROM categories
            WHERE user_id = :user_id AND name IN ('Voiture', 'Restaurants / livraison')
            """
        ),
        {"user_id": user.id},
    )
    categories = {row.name: row.id for row in category_rows.mappings().all()}

    # 4. Import CSV bancaire.
    with (FIXTURES_DIR / "transactions_credit_mutuel_sample.csv").open("rb") as csv_file:
        import_response = await client.post(
            "/transactions/import",
            headers=headers,
            data={"account_id": account_id},
            files={"file": ("transactions.csv", csv_file, "text/csv")},
        )
    assert import_response.status_code == 201, import_response.text
    assert import_response.json()["imported"] == 8

    transactions = await client.get("/transactions", headers=headers)
    assert transactions.status_code == 200
    fulli_transaction = next(
        item for item in transactions.json() if "FULLI" in item["label_raw"]
    )

    # 5. Catégorisation automatique avec une règle métier active.
    await db_session.execute(
        text(
            """
            INSERT INTO categorization_rules (
                user_id, name, priority, match_type, pattern,
                category_id, confidence_score, is_active
            ) VALUES (
                :user_id, 'Péage Fulli', 1, 'contains', 'fulli',
                :category_id, 0.9300, true
            )
            """
        ),
        {"user_id": user.id, "category_id": categories["Voiture"]},
    )
    await db_session.commit()
    auto_category = await CategorizationService(db_session).resolve_category(
        user_id=UUID(str(user.id)),
        label_raw=fulli_transaction["label_raw"],
        amount=Decimal(fulli_transaction["amount"]),
    )
    assert auto_category.category_id == categories["Voiture"]
    assert auto_category.applied_rule == "Péage Fulli"

    # 6. Correction manuelle de catégorie sur la transaction importée.
    patch_response = await client.patch(
        f"/transactions/{fulli_transaction['id']}/category",
        headers=headers,
        json={
            "category_id": str(categories["Restaurants / livraison"]),
            "notes": "Correction manuelle depuis le test d'intégration",
            "confidence_score": "1.0000",
            "learning_scope": "transaction_only",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["category_id"] == str(
        categories["Restaurants / livraison"]
    )

    # 7. Upload document.
    document_bytes = b"FULLI SAS\nFacture FA-2026-0007\nDate : 09/07/2026\nTotal TTC : 28,40 EUR"
    upload_response = await client.post(
        "/documents/upload",
        headers=headers,
        data={"document_type": "invoice", "title": "Facture Fulli"},
        files={"file": ("fulli.txt", document_bytes, "text/plain")},
    )
    assert upload_response.status_code == 201, upload_response.text
    document_id = upload_response.json()["document"]["id"]

    # 8. Extraction texte enregistrée explicitement.
    extract_response = await client.post(
        f"/documents/{document_id}/extract",
        headers=headers,
        json={
            "extracted_text": document_bytes.decode(),
            "extraction_status": "completed",
            "issuer": "FULLI SAS",
            "issue_date": "2026-07-09",
            "amount": "28.40",
            "currency": "EUR",
            "confidence_score": "0.9500",
        },
    )
    assert extract_response.status_code == 200, extract_response.text
    assert "Facture FA-2026-0007" in extract_response.json()["extracted_text"]

    # 9. Rapprochement document/transaction.
    link_response = await client.post(
        f"/documents/{document_id}/link-transaction",
        headers=headers,
        json={"transaction_id": fulli_transaction["id"]},
    )
    assert link_response.status_code == 200, link_response.text
    assert link_response.json()["linked_transaction_id"] == fulli_transaction["id"]

    # 10. Création rappel.
    reminder_response = await client.post(
        "/reminders",
        headers=headers,
        json={
            "title": "Relire facture Fulli",
            "description": "Contrôler la pièce jointe importée",
            "due_date": "2026-08-20",
            "reminder_date": "2026-08-15",
            "severity": "warning",
            "notification_channels": ["in_app", "email"],
        },
    )
    assert reminder_response.status_code == 201, reminder_response.text
    assert reminder_response.json()["status"] == "pending"

    # 11. Lecture dashboard mensuel.
    dashboard_response = await client.get(
        "/dashboard/monthly-summary?month=2026-07", headers=headers
    )
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert dashboard["month"] == "2026-07"
    assert Decimal(dashboard["expenses"]) > Decimal("0")
    assert dashboard["top_categories"]
