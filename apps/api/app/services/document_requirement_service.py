"""Règles métier pour identifier les transactions nécessitant un justificatif."""

from __future__ import annotations

from decimal import Decimal

from app.core.config import get_settings

PROFESSIONAL_OR_TAX_TAGS = ("professional", "professionnel", "business", "tax", "fiscal")


def default_document_amount_threshold() -> Decimal:
    """Retourne le seuil configurable au-delà duquel une dépense requiert un justificatif."""

    return Decimal(str(get_settings().document_required_amount_threshold))


def document_requirement_condition(table_alias: str = "t") -> str:
    """Condition SQL des transactions pertinentes sans justificatif.

    Une transaction est pertinente si elle est une dépense non interne, non liée à un
    document, hors catégories ignorées par l'utilisateur, et si elle dépasse le seuil,
    appartient à une catégorie marquée comme nécessitant un justificatif, ou porte un
    tag professionnel/fiscal dans ``raw_data_json.tags``.
    """

    return f"""
        {table_alias}.linked_document_id IS NULL
        AND {table_alias}.amount < 0
        AND {table_alias}.is_internal_transfer = false
        AND (
            {table_alias}.category_id IS NULL
            OR NOT ({table_alias}.category_id = ANY(:ignored_document_category_ids))
        )
        AND (
            abs({table_alias}.amount) >= :document_amount_threshold
            OR coalesce(c.requires_document, false) = true
            OR EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(
                    CASE
                        WHEN jsonb_typeof({table_alias}.raw_data_json->'tags') = 'array'
                        THEN {table_alias}.raw_data_json->'tags'
                        ELSE '[]'::jsonb
                    END
                ) AS transaction_tags(tag)
                WHERE lower(transaction_tags.tag) = ANY(:document_required_tags)
            )
        )
    """
