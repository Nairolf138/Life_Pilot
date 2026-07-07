"""Importateur CSV bancaire configurable pour Life Pilot."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO, TextIO
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.transaction import TransactionImportItem, TransactionImportRequest


class CsvBankColumnMapping(BaseModel):
    """Association entre les champs transactionnels et les colonnes CSV."""

    booking_date: str = Field(default="date_operation")
    value_date: str | None = Field(default="date_valeur")
    label_raw: str = Field(default="libelle")
    amount: str = Field(default="montant")
    currency: str | None = Field(default="devise")
    external_id: str | None = None


class CsvBankImportConfig(BaseModel):
    """Configuration d'import CSV bancaire."""

    account_id: UUID
    mapping: CsvBankColumnMapping = Field(default_factory=CsvBankColumnMapping)
    delimiter: str = ";"
    encoding: str = "utf-8-sig"
    default_currency: str = "EUR"
    date_formats: tuple[str, ...] = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


@dataclass(frozen=True, slots=True)
class CsvBankImportParseResult:
    """Résultat de parsing avant persistance."""

    request: TransactionImportRequest
    ignored_duplicates: int


class CsvBankImporter:
    """Convertit un CSV bancaire en payload d'import de transactions."""

    def __init__(self, config: CsvBankImportConfig) -> None:
        self._config = config

    def parse_path(self, path: str | Path) -> CsvBankImportParseResult:
        """Parse un fichier CSV depuis le disque."""

        with Path(path).open("r", encoding=self._config.encoding, newline="") as stream:
            return self.parse_text_stream(stream, source_name=str(path))

    def parse_upload(
        self,
        upload: BinaryIO,
        *,
        filename: str | None = None,
    ) -> CsvBankImportParseResult:
        """Parse un flux d'upload FastAPI ou tout flux binaire CSV."""

        content = upload.read()
        if isinstance(content, str):
            text = content
        else:
            text = content.decode(self._config.encoding)
        rows = text.splitlines()
        return self._parse_rows(rows, source_name=filename or "upload.csv")

    def parse_text_stream(
        self,
        stream: TextIO,
        *,
        source_name: str = "transactions.csv",
    ) -> CsvBankImportParseResult:
        """Parse un flux texte CSV."""

        return self._parse_rows(stream, source_name=source_name)

    def _parse_rows(
        self,
        rows: Any,
        *,
        source_name: str,
    ) -> CsvBankImportParseResult:
        reader = csv.DictReader(rows, delimiter=self._config.delimiter)
        transactions: list[TransactionImportItem] = []
        seen: set[tuple[date, Decimal, str, str]] = set()
        duplicate_count = 0
        for line_number, row in enumerate(reader, start=2):
            item = self._parse_row(
                row, line_number=line_number, source_name=source_name
            )
            dedup_key = (
                item.booking_date,
                item.amount,
                _normalize_label(item.label_raw),
                item.currency,
            )
            if dedup_key in seen:
                duplicate_count += 1
                continue
            seen.add(dedup_key)
            transactions.append(item)
        return CsvBankImportParseResult(
            request=TransactionImportRequest(transactions=transactions),
            ignored_duplicates=duplicate_count,
        )

    def _parse_row(
        self,
        row: dict[str, str | None],
        *,
        line_number: int,
        source_name: str,
    ) -> TransactionImportItem:
        mapping = self._config.mapping
        booking_date = self._parse_date(
            _required(row, mapping.booking_date), mapping.booking_date
        )
        value_date = None
        if mapping.value_date:
            raw_value_date = _optional(row, mapping.value_date)
            if raw_value_date:
                value_date = self._parse_date(raw_value_date, mapping.value_date)
        label_raw = _required(row, mapping.label_raw).strip()
        amount = _parse_amount(_required(row, mapping.amount))
        currency = self._config.default_currency
        if mapping.currency:
            currency = (
                _optional(row, mapping.currency) or self._config.default_currency
            ).strip()
        external_id = None
        if mapping.external_id:
            external_id = _optional(row, mapping.external_id)
        if not external_id:
            external_id = _stable_external_id(
                self._config.account_id,
                booking_date,
                amount,
                label_raw,
                line_number,
                source_name,
            )
        return TransactionImportItem(
            account_id=self._config.account_id,
            external_id=external_id,
            booking_date=booking_date,
            value_date=value_date,
            label_raw=label_raw,
            amount=amount,
            currency=currency,
            raw_data_json={
                "source": source_name,
                "line_number": line_number,
                "csv_row": row,
            },
        )

    def _parse_date(self, value: str, column: str) -> date:
        for date_format in self._config.date_formats:
            try:
                return datetime.strptime(value.strip(), date_format).date()
            except ValueError:
                continue
        raise ValueError(f"Date invalide dans la colonne {column!r}: {value!r}.")


def config_from_json(
    mapping_json: str | None, *, account_id: UUID
) -> CsvBankImportConfig:
    """Construit une configuration à partir d'un JSON optionnel."""

    payload: dict[str, Any] = {"account_id": account_id}
    if mapping_json:
        decoded = json.loads(mapping_json)
        if "mapping" in decoded:
            payload.update(decoded)
        else:
            payload["mapping"] = decoded
    return CsvBankImportConfig.model_validate(payload)


def _required(row: dict[str, str | None], column: str) -> str:
    value = row.get(column)
    if value is None or not value.strip():
        raise ValueError(f"Colonne CSV obligatoire absente ou vide: {column!r}.")
    return value


def _optional(row: dict[str, str | None], column: str) -> str | None:
    value = row.get(column)
    if value is None or not value.strip():
        return None
    return value


def _parse_amount(value: str) -> Decimal:
    normalized = re.sub(r"[^0-9,.-]", "", value.strip()).replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"Montant CSV invalide: {value!r}.") from exc


def _stable_external_id(
    account_id: UUID,
    booking_date: date,
    amount: Decimal,
    label_raw: str,
    line_number: int,
    source_name: str,
) -> str:
    raw = "|".join(
        (
            str(account_id),
            booking_date.isoformat(),
            str(amount),
            _normalize_label(label_raw),
            source_name,
            str(line_number),
        )
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().split())
