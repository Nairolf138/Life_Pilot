"""Fournisseurs OCR interchangeables de Life Pilot."""

from app.services.ocr.local_tesseract import LocalTesseractOcrProvider
from app.services.ocr.provider import (
    OCR_STATUS_FAILED,
    OCR_STATUS_PROCESSED,
    OCR_STATUS_UNAVAILABLE,
    OcrExtractionResult,
    OcrProvider,
)

__all__ = [
    "LocalTesseractOcrProvider",
    "OCR_STATUS_FAILED",
    "OCR_STATUS_PROCESSED",
    "OCR_STATUS_UNAVAILABLE",
    "OcrExtractionResult",
    "OcrProvider",
]
