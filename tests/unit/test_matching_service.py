from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.matching_service import MatchingLevel, MatchingService, matching_level


def test_matching_level_boundaries():
    assert matching_level(100) == MatchingLevel.AUTOMATIC
    assert matching_level(90) == MatchingLevel.AUTOMATIC
    assert matching_level(89) == MatchingLevel.PROPOSAL
    assert matching_level(70) == MatchingLevel.PROPOSAL
    assert matching_level(69) == MatchingLevel.WEAK
    assert matching_level(40) == MatchingLevel.WEAK
    assert matching_level(39) == MatchingLevel.UNMATCHED


def test_score_candidate_adds_all_spec_criteria():
    document = SimpleNamespace(
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
        category_id=uuid4(),
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
    assert candidate.reasons == (
        "amount_exact",
        "date_within_3_days",
        "merchant_or_provider_similar",
        "known_provider",
        "category_coherent",
        "known_reference_or_contract",
    )
