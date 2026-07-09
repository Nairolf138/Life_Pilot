"""Contrats d'intégration OCR pour les documents utilisateur."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

OCR_STATUS_PROCESSED = "ocr_processed"
OCR_STATUS_UNAVAILABLE = "ocr_unavailable"
OCR_STATUS_FAILED = "ocr_failed"


@dataclass(frozen=True, slots=True)
class OcrExtractionResult:
    """Résultat normalisé retourné par un fournisseur OCR."""

    text: str | None
    confidence_score: Decimal | None
    status: str = OCR_STATUS_PROCESSED


class OcrProvider(Protocol):
    """Interface commune aux fournisseurs OCR remplaçables par environnement."""

    def extract_text(
        self,
        *,
        content: bytes,
        mime_type: str | None,
        filename: str | None = None,
    ) -> OcrExtractionResult:
        """Convertit un PDF ou une image en texte avec un statut de confiance."""
