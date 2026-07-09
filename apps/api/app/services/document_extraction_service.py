"""Extraction initiale de texte et métadonnées depuis les documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO

from app.services.ocr import OCR_STATUS_PROCESSED, OcrProvider

EXTRACTION_STATUS_PENDING = "pending"
EXTRACTION_STATUS_TEXT_EXTRACTED = "text_extracted"
EXTRACTION_STATUS_OCR_REQUIRED = "ocr_required"
EXTRACTION_STATUS_OCR_PROCESSED = "ocr_processed"
EXTRACTION_STATUS_FAILED = "failed"

USABLE_TEXT_MIN_LENGTH = 20


@dataclass(frozen=True, slots=True)
class DocumentExtractionResult:
    """Résultat normalisé d'une extraction documentaire."""

    extracted_text: str | None
    extraction_status: str
    confidence_score: Decimal
    issuer: str | None = None
    issue_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None


class DocumentExtractionService:
    """Extrait le texte d'un PDF ou d'une image et quelques champs métier simples."""

    def __init__(self, ocr_provider: OcrProvider | None = None) -> None:
        self._ocr_provider = ocr_provider

    def extract_document(
        self,
        content: bytes,
        *,
        mime_type: str | None,
        filename: str | None = None,
    ) -> DocumentExtractionResult:
        """Extrait un document PDF ou image, avec bascule OCR si nécessaire."""

        if is_image_mime_type(mime_type):
            return self._extract_with_ocr(
                content,
                mime_type=mime_type,
                filename=filename,
                fallback_status=EXTRACTION_STATUS_OCR_REQUIRED,
            )
        if is_pdf_mime_type(mime_type) or looks_like_pdf(content):
            native_extraction = self.extract_pdf(content)
            if native_extraction.extraction_status != EXTRACTION_STATUS_OCR_REQUIRED:
                return native_extraction
            ocr_extraction = self._extract_with_ocr(
                content,
                mime_type=mime_type,
                filename=filename,
                fallback_status=EXTRACTION_STATUS_OCR_REQUIRED,
            )
            if ocr_extraction.extraction_status == EXTRACTION_STATUS_OCR_PROCESSED:
                return ocr_extraction
            return native_extraction
        return self._extract_with_ocr(
            content,
            mime_type=mime_type,
            filename=filename,
            fallback_status=EXTRACTION_STATUS_FAILED,
        )

    def extract_pdf(self, content: bytes) -> DocumentExtractionResult:
        """Extrait le texte natif d'un PDF, sans OCR."""

        from pypdf import PdfReader

        try:
            reader = PdfReader(BytesIO(content))
            pages_text = [page.extract_text() or "" for page in reader.pages]
        except Exception:
            return DocumentExtractionResult(
                extracted_text=None,
                extraction_status=EXTRACTION_STATUS_FAILED,
                confidence_score=Decimal("0"),
            )

        extracted_text = normalize_extracted_text("\n".join(pages_text))
        if not is_usable_text(extracted_text):
            return DocumentExtractionResult(
                extracted_text=extracted_text or None,
                extraction_status=EXTRACTION_STATUS_OCR_REQUIRED,
                confidence_score=Decimal("0.10"),
            )

        metadata = extract_business_fields(extracted_text)
        confidence_score = score_text_extraction(extracted_text, metadata)
        return DocumentExtractionResult(
            extracted_text=extracted_text,
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            confidence_score=confidence_score,
            issuer=metadata.issuer,
            issue_date=metadata.issue_date,
            amount=metadata.amount,
            currency=metadata.currency,
        )

    def _extract_with_ocr(
        self,
        content: bytes,
        *,
        mime_type: str | None,
        filename: str | None,
        fallback_status: str,
    ) -> DocumentExtractionResult:
        if self._ocr_provider is None:
            return DocumentExtractionResult(
                extracted_text=None,
                extraction_status=fallback_status,
                confidence_score=Decimal("0"),
            )

        try:
            ocr_result = self._ocr_provider.extract_text(
                content=content,
                mime_type=mime_type,
                filename=filename,
            )
        except Exception:
            return DocumentExtractionResult(
                extracted_text=None,
                extraction_status=EXTRACTION_STATUS_FAILED,
                confidence_score=Decimal("0"),
            )

        extracted_text = normalize_extracted_text(ocr_result.text or "")
        if (
            ocr_result.status != OCR_STATUS_PROCESSED
            or not is_usable_text(extracted_text)
        ):
            return DocumentExtractionResult(
                extracted_text=extracted_text or None,
                extraction_status=fallback_status,
                confidence_score=ocr_result.confidence_score or Decimal("0"),
            )

        metadata = extract_business_fields(extracted_text)
        return DocumentExtractionResult(
            extracted_text=extracted_text,
            extraction_status=EXTRACTION_STATUS_OCR_PROCESSED,
            confidence_score=normalize_confidence_score(ocr_result.confidence_score),
            issuer=metadata.issuer,
            issue_date=metadata.issue_date,
            amount=metadata.amount,
            currency=metadata.currency,
        )


@dataclass(frozen=True, slots=True)
class ExtractedBusinessFields:
    """Champs métier détectés dans le texte d'un document."""

    issuer: str | None = None
    issue_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None


DATE_PATTERNS = (
    re.compile(r"\b(?P<day>\d{1,2})[/.\-](?P<month>\d{1,2})[/.\-](?P<year>\d{2,4})\b"),
    re.compile(r"\b(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\b"),
)
AMOUNT_PATTERN = re.compile(
    r"(?i)(?:total\s+(?:ttc|à\s+payer)|montant\s+(?:ttc|total)|net\s+à\s+payer|à\s+payer)"
    r"[^\d\n]{0,30}(?P<amount>\d{1,3}(?:[\s.]\d{3})*(?:[,.]\d{2})|\d+(?:[,.]\d{2}))"
    r"\s*(?P<currency>€|eur|euro|euros|usd|\$|chf|gbp)?"
)
FALLBACK_AMOUNT_PATTERN = re.compile(
    r"(?P<amount>\d{1,3}(?:[\s.]\d{3})*(?:[,.]\d{2})|\d+(?:[,.]\d{2}))"
    r"\s*(?P<currency>€|eur|euro|euros|usd|\$|chf|gbp)",
    re.IGNORECASE,
)
LEGAL_SUFFIX_PATTERN = re.compile(
    r"\b(?:sarl|sas|sa|eurl|sasu|association|auto-entrepreneur|micro-entreprise)\b",
    re.IGNORECASE,
)
NOISY_ISSUER_PREFIXES = ("facture", "invoice", "reçu", "receipt", "date", "total")


def normalize_extracted_text(text: str) -> str:
    """Nettoie les blancs tout en conservant les lignes significatives."""

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def is_usable_text(text: str | None) -> bool:
    """Détermine si le texte PDF est suffisant pour éviter un passage OCR."""

    if text is None:
        return False
    alphanumeric_count = sum(character.isalnum() for character in text)
    return alphanumeric_count >= USABLE_TEXT_MIN_LENGTH


def is_pdf_mime_type(mime_type: str | None) -> bool:
    """Indique si le type MIME correspond à un PDF."""

    return (mime_type or "").lower() == "application/pdf"


def is_image_mime_type(mime_type: str | None) -> bool:
    """Indique si le type MIME correspond à une image prise en charge par OCR."""

    return (mime_type or "").lower().startswith("image/")


def looks_like_pdf(content: bytes) -> bool:
    """Détecte rapidement un PDF lorsque le type MIME est absent."""

    return content.startswith(b"%PDF")


def extract_business_fields(text: str) -> ExtractedBusinessFields:
    """Extrait date, montant et émetteur avec des heuristiques déterministes."""

    amount, currency = extract_amount(text)
    return ExtractedBusinessFields(
        issuer=extract_issuer(text),
        issue_date=extract_issue_date(text),
        amount=amount,
        currency=currency,
    )


def extract_issue_date(text: str) -> date | None:
    """Retourne la première date plausible détectée dans le document."""

    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            year = int(match.group("year"))
            if year < 100:
                year += 2000 if year < 70 else 1900
            try:
                return date(year, int(match.group("month")), int(match.group("day")))
            except ValueError:
                continue
    return None


def extract_amount(text: str) -> tuple[Decimal | None, str | None]:
    """Retourne le montant total prioritaire et sa devise."""

    for pattern in (AMOUNT_PATTERN, FALLBACK_AMOUNT_PATTERN):
        matches = list(pattern.finditer(text))
        if matches:
            match = matches[-1]
            return parse_decimal(match.group("amount")), normalize_currency(
                match.group("currency")
            )
    return None, None


def extract_issuer(text: str) -> str | None:
    """Infère l'émetteur depuis les premières lignes non bruitées."""

    candidates = []
    for line in text.splitlines()[:12]:
        normalized = line.strip(" :-\t")
        if len(normalized) < 3 or any(char.isdigit() for char in normalized[:4]):
            continue
        if normalized.lower().startswith(NOISY_ISSUER_PREFIXES):
            continue
        candidates.append(normalized)
        if LEGAL_SUFFIX_PATTERN.search(normalized):
            return normalized[:255]
    return candidates[0][:255] if candidates else None


def parse_decimal(value: str) -> Decimal | None:
    """Convertit un montant français ou international en Decimal."""

    normalized = value.replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def normalize_currency(value: str | None) -> str | None:
    """Normalise les symboles et libellés de devise en code ISO."""

    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"€", "eur", "euro", "euros"}:
        return "EUR"
    if normalized in {"$", "usd"}:
        return "USD"
    if normalized == "chf":
        return "CHF"
    if normalized == "gbp":
        return "GBP"
    return normalized.upper()


def score_text_extraction(text: str, metadata: ExtractedBusinessFields) -> Decimal:
    """Calcule une confiance simple basée sur texte et champs extraits."""

    score = Decimal("0.55")
    if len(text) >= 100:
        score += Decimal("0.15")
    if metadata.issuer:
        score += Decimal("0.10")
    if metadata.issue_date:
        score += Decimal("0.10")
    if metadata.amount:
        score += Decimal("0.10")
    return min(score, Decimal("0.95")).quantize(Decimal("0.0001"))


def normalize_confidence_score(score: Decimal | None) -> Decimal:
    """Normalise la confiance OCR dans l'intervalle stockable en base."""

    if score is None:
        return Decimal("0")
    return min(max(score, Decimal("0")), Decimal("1")).quantize(Decimal("0.0001"))
