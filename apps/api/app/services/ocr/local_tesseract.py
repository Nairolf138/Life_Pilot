"""Préparation d'une future implémentation OCR locale avec Tesseract."""

from __future__ import annotations

from decimal import Decimal

from app.services.ocr.provider import (
    OCR_STATUS_UNAVAILABLE,
    OcrExtractionResult,
)


class LocalTesseractOcrProvider:
    """Fournisseur local prévu pour piloter Tesseract dans un worker Python."""

    def extract_text(
        self,
        *,
        content: bytes,
        mime_type: str | None,
        filename: str | None = None,
    ) -> OcrExtractionResult:
        """Retourne un statut explicite tant que Tesseract n'est pas branché."""

        return OcrExtractionResult(
            text=None,
            confidence_score=Decimal("0"),
            status=OCR_STATUS_UNAVAILABLE,
        )
