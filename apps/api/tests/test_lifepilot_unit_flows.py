from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.schemas.reminder import NotificationChannel, ReminderCreate, ReminderSeverity
from app.services.categorization_service import (
    DEFAULT_CONFIDENCE_SCORE,
    CategorizationRule,
    CategorizationService,
)
from app.services.document_extraction_service import extract_business_fields
from app.services.importers.csv_bank_importer import (
    CsvBankImportConfig,
    CsvBankImporter,
)
from app.services.manual_correction_service import ManualCorrectionService
from app.services.matching_service import MatchingLevel, MatchingService
from app.services.monthly_summary_service import (
    MonthlyCategorySummary,
    MonthlySummary,
    month_bounds,
)
from app.services.reminder_engine import ReminderEngineSeverity, _candidate_from_row
from app.services.transaction_service import normalized_label

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000001")
USER_ID = UUID("00000000-0000-0000-0000-000000000002")
CATEGORY_ID = UUID("00000000-0000-0000-0000-000000000003")
SUBCATEGORY_ID = UUID("00000000-0000-0000-0000-000000000004")


def test_parsing_transaction_csv_uses_fixture_rows_and_amounts():
    importer = CsvBankImporter(CsvBankImportConfig(account_id=ACCOUNT_ID))

    result = importer.parse_path(FIXTURES_DIR / "transactions_credit_mutuel_sample.csv")

    assert result.ignored_duplicates == 0
    assert len(result.request.transactions) == 8
    first = result.request.transactions[0]
    assert first.account_id == ACCOUNT_ID
    assert first.booking_date == date(2026, 7, 5)
    assert first.value_date == date(2026, 7, 6)
    assert first.label_raw == "CARTE 04/07 FULLI AUTOROUTE A6"
    assert first.amount == Decimal("-28.40")
    assert first.currency == "EUR"
    assert first.raw_data_json["source"].endswith(
        "transactions_credit_mutuel_sample.csv"
    )


def test_deduplication_transaction_ignores_duplicate_csv_line():
    csv_content = """date_operation;date_valeur;libelle;montant;devise
02/07/2026;02/07/2026;CB FULLI AUTOROUTE;-42,80;EUR
02/07/2026;02/07/2026; cb   fulli autoroute ;-42,80;EUR
03/07/2026;03/07/2026;UBER EATS;-18,50;EUR
""".splitlines()
    importer = CsvBankImporter(CsvBankImportConfig(account_id=ACCOUNT_ID))

    result = importer.parse_text_stream(iter(csv_content), source_name="inline.csv")

    assert result.ignored_duplicates == 1
    assert [item.label_raw for item in result.request.transactions] == [
        "CB FULLI AUTOROUTE",
        "UBER EATS",
    ]
    assert normalized_label(" cb   fulli autoroute ") == normalized_label(
        "CB FULLI AUTOROUTE"
    )


class StaticRuleCategorizationService(CategorizationService):
    def __init__(self, rules):
        super().__init__(session=None)
        self._rules = rules

    async def ensure_initial_system_rules(self, user_id):
        return None

    async def _list_active_rules(self, user_id):
        return self._rules

    async def _get_unknown_category_id(self, user_id):
        return None


def rule(*, match_type: str, pattern: str, name: str = "test rule"):
    return CategorizationRule(
        id=uuid4(),
        name=name,
        priority=1,
        match_type=match_type,
        pattern=pattern,
        provider_filter=None,
        amount_min=None,
        amount_max=None,
        category_id=CATEGORY_ID,
        subcategory_id=SUBCATEGORY_ID,
        confidence_score=None,
    )


def test_categorisation_par_regle_contains():
    service = StaticRuleCategorizationService(
        [rule(match_type="contains", pattern="fulli", name="Péage Fulli")]
    )

    result = asyncio.run(
        service.resolve_category(
            user_id=USER_ID,
            label_raw="CB FULLI AUTOROUTE A10",
            amount=Decimal("-42.80"),
        )
    )

    assert result.category_id == CATEGORY_ID
    assert result.subcategory_id == SUBCATEGORY_ID
    assert result.confidence_score == DEFAULT_CONFIDENCE_SCORE
    assert result.applied_rule == "Péage Fulli"


def test_categorisation_par_regex():
    service = StaticRuleCategorizationService(
        [rule(match_type="regex", pattern=r"uber\s+eats", name="Livraison repas")]
    )

    result = asyncio.run(
        service.resolve_category(
            user_id=USER_ID,
            label_raw="Paiement carte UBER   EATS Paris",
            amount=Decimal("-18.50"),
        )
    )

    assert result.category_id == CATEGORY_ID
    assert result.applied_rule == "Livraison repas"


class RecordingAuditLogService:
    def __init__(self):
        self.entries = []

    async def record(self, entry):
        self.entries.append(entry)


def test_correction_manuelle_de_categorie_est_auditee():
    audit_service = RecordingAuditLogService()
    service = ManualCorrectionService(audit_service)
    transaction_id = uuid4()

    asyncio.run(
        service.audit_manual_update(
            user_id=USER_ID,
            entity_type="transaction",
            entity_id=transaction_id,
            before_state={"category_id": None},
            after_state={"category_id": str(CATEGORY_ID)},
            reason="Correction de catégorie depuis l'interface",
        )
    )

    entry = audit_service.entries[0]
    assert entry.user_id == USER_ID
    assert entry.entity_type == "transaction"
    assert entry.entity_id == transaction_id
    assert entry.before_state == {"category_id": None}
    assert entry.after_state == {"category_id": str(CATEGORY_ID)}
    assert entry.reason == "Correction de catégorie depuis l'interface"


def test_extraction_date_montant_depuis_texte_document():
    text = """
    FULLI SAS
    Facture FA-2026-0007
    Date : 09/07/2026
    Total TTC : 42,80 €
    """

    fields = extract_business_fields(text)

    assert fields.issuer == "FULLI SAS"
    assert fields.issue_date == date(2026, 7, 9)
    assert fields.amount == Decimal("42.80")
    assert fields.currency == "EUR"


def test_scoring_rapprochement_facture_transaction():
    document = SimpleNamespace(
        id=uuid4(),
        amount=Decimal("42.80"),
        due_date=date(2026, 7, 9),
        issue_date=None,
        issuer="Fulli",
        provider=None,
        document_type="facture peage",
        title="Facture Fulli contrat ABC123456",
        extracted_text="Contrat ABC123456",
        tags=["transport"],
    )
    transaction = SimpleNamespace(
        id=uuid4(),
        amount=Decimal("-42.80"),
        booking_date=date(2026, 7, 10),
        merchant_name="FULLI",
        label_clean="FULLI paiement ABC123456",
        label_raw="CB FULLI ABC123456",
        category_id=CATEGORY_ID,
        category_name="transport",
        known_provider=True,
        linked_document_id=None,
        notes=None,
        raw_data_json={},
        currency="EUR",
    )

    candidate = MatchingService(session=None).score_candidate(
        document=document,
        transaction=transaction,
    )

    assert candidate.score == 100
    assert candidate.level == MatchingLevel.AUTOMATIC
    assert "amount_exact" in candidate.reasons
    assert "date_within_3_days" in candidate.reasons


def test_generation_rappel_cree_candidat_notification_priorise():
    reminder_id = uuid4()
    row = SimpleNamespace(
        id=reminder_id,
        user_id=USER_ID,
        title="Contrôle technique à renouveler",
        description="Préparer le rendez-vous",
        due_date=date(2026, 8, 20),
        reminder_date=date(2026, 8, 5),
        severity="urgent",
        notification_channels=["email", "in_app"],
    )

    candidate = _candidate_from_row(row)

    assert candidate.reminder_id == reminder_id
    assert candidate.severity == ReminderEngineSeverity.URGENT
    assert candidate.priority == 2
    assert candidate.channels == ["email", "in_app"]
    assert candidate.deduplication_key == f"reminder:{reminder_id}:2026-08-20"


def test_schema_rappel_manuel_explicite_canaux_et_severite():
    reminder = ReminderCreate(
        title="Envoyer facture comptable",
        due_date=date(2026, 8, 31),
        reminder_date=date(2026, 8, 25),
        severity=ReminderSeverity.WARNING,
        notification_channels=[NotificationChannel.EMAIL],
    )

    assert reminder.title == "Envoyer facture comptable"
    assert reminder.source_type == "manual"
    assert reminder.notification_channels == [NotificationChannel.EMAIL]


def test_calcul_synthese_mensuelle_dataclass_et_bornes():
    period_start, period_end = month_bounds("2026-07")
    transport = MonthlyCategorySummary(
        category_id=CATEGORY_ID,
        category_name="Transport",
        amount=Decimal("42.80"),
        transaction_count=1,
    )
    alimentation = MonthlyCategorySummary(
        category_id=SUBCATEGORY_ID,
        category_name="Restaurants / livraison",
        amount=Decimal("18.50"),
        transaction_count=1,
    )
    income = Decimal("3500.00")
    expenses = transport.amount + alimentation.amount

    summary = MonthlySummary(
        month="2026-07",
        period_start=period_start,
        period_end=period_end,
        income=income,
        expenses=expenses,
        estimated_savings=income - expenses,
        estimated_remaining=income - expenses,
        expenses_by_category=[transport, alimentation],
        top_categories=[transport, alimentation],
        uncategorized_transactions=[],
        low_confidence_transactions=[],
        transactions_without_document=[],
        financial_unmatched_documents_count=0,
        transactions_without_document_count=0,
        transactions_without_document_amount=Decimal("0"),
    )

    assert summary.period_start == date(2026, 7, 1)
    assert summary.period_end == date(2026, 7, 31)
    assert summary.income == Decimal("3500.00")
    assert summary.expenses == Decimal("61.30")
    assert summary.estimated_savings == Decimal("3438.70")
    assert [category.category_name for category in summary.top_categories] == [
        "Transport",
        "Restaurants / livraison",
    ]
