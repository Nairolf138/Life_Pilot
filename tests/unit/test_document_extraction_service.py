from datetime import date
from decimal import Decimal

from app.services.document_extraction_service import (
    EXTRACTION_STATUS_OCR_PROCESSED,
    EXTRACTION_STATUS_OCR_REQUIRED,
    DocumentExtractionService,
    extract_amount,
    extract_business_fields,
    is_usable_text,
)
from app.services.ocr import OcrExtractionResult


def test_extract_business_fields_detects_issuer_date_and_amount():
    text = """
    ACME SERVICES SAS
    10 rue de Paris
    Facture FAC-2026-001
    Date : 08/07/2026
    Total TTC : 1 234,56 €
    """

    fields = extract_business_fields(text)

    assert fields.issuer == "ACME SERVICES SAS"
    assert fields.issue_date == date(2026, 7, 8)
    assert fields.amount == Decimal("1234.56")
    assert fields.currency == "EUR"


def test_extract_amount_prefers_last_total_amount():
    text = """
    Sous-total : 100,00 EUR
    TVA : 20,00 EUR
    Net à payer : 120,00 EUR
    """

    amount, currency = extract_amount(text)

    assert amount == Decimal("120.00")
    assert currency == "EUR"


def test_short_or_empty_text_requires_ocr():
    assert not is_usable_text("")
    assert not is_usable_text("--- 12 €")
    assert EXTRACTION_STATUS_OCR_REQUIRED == "ocr_required"


class StubOcrProvider:
    def extract_text(self, *, content, mime_type, filename=None):
        return OcrExtractionResult(
            text="""
            ACME SERVICES SAS
            Date : 08/07/2026
            Total TTC : 1 234,56 €
            """,
            confidence_score=Decimal("0.87"),
        )


def test_image_document_uses_ocr_provider_and_marks_processed():
    service = DocumentExtractionService(ocr_provider=StubOcrProvider())

    result = service.extract_document(
        b"fake image bytes",
        mime_type="image/png",
        filename="invoice.png",
    )

    assert result.extraction_status == EXTRACTION_STATUS_OCR_PROCESSED
    assert result.extracted_text is not None
    assert "ACME SERVICES SAS" in result.extracted_text
    assert result.confidence_score == Decimal("0.8700")
    assert result.issuer == "ACME SERVICES SAS"
    assert result.amount == Decimal("1234.56")
