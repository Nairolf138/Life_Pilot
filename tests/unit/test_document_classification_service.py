from datetime import date

from app.services.document_classification_service import (
    DocumentClassificationInput,
    classify_tax_document,
)


def classify(document_type, *, tags=None, issuer=None, issue_date=date(2026, 4, 15)):
    return classify_tax_document(
        DocumentClassificationInput(
            document_type=document_type,
            tags=tags or [],
            issuer=issuer,
            issue_date=issue_date,
        )
    )


def test_classifies_tax_notice_and_adds_tags():
    result = classify("Avis d'impôt sur les revenus")

    assert result.fiscal_type == "tax_notice"
    assert result.tax_year == 2026
    assert result.tags == ["fiscal", "tax:tax_notice"]


def test_classifies_previous_declaration_from_tags():
    result = classify("pdf", tags=["Déclaration précédente", "archive"])

    assert result.fiscal_type == "previous_tax_declaration"
    assert result.tags == [
        "Déclaration précédente",
        "archive",
        "fiscal",
        "tax:previous_tax_declaration",
    ]


def test_classifies_bank_tax_document_from_issuer_and_type():
    result = classify("IFU", issuer="Crédit Mutuel")

    assert result.fiscal_type == "bank_tax_document"


def test_classifies_broker_and_crypto_exports():
    assert classify("transactions", issuer="Binance").fiscal_type == "binance_export"
    assert classify("export fiscal", issuer="eToro").fiscal_type == "etoro_export"


def test_classifies_income_proof_and_manual_prefilled_declaration():
    assert classify("Bulletin de salaire").fiscal_type == "income_proof"
    assert (
        classify("Déclaration préremplie importée manuellement").fiscal_type
        == "manual_prefilled_declaration"
    )


def test_ignores_non_fiscal_document_and_keeps_existing_tags():
    result = classify("facture", tags=["maison"], issue_date=None)

    assert result.fiscal_type is None
    assert result.tax_year is None
    assert result.tags == ["maison"]
