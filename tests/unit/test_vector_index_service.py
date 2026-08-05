from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.vector_index_service import VectorIndexService, chunk_text


def test_vector_index_is_disabled_when_provider_is_none():
    service = VectorIndexService(Settings(LLM_PROVIDER="none"))

    assert service.enabled is False


@pytest.mark.anyio
async def test_vector_index_stores_document_source_and_searches_passages():
    service = VectorIndexService(Settings(LLM_PROVIDER="local"))
    document_id = uuid4()

    passages = await service.index_document_text(
        document_id=document_id,
        text="Assurance habitation échéance septembre. Contrat auto sans rapport.",
        source_label="documents/assurance.pdf",
        metadata={"document_type": "contrat"},
    )
    results = await service.search_relevant_passages("assurance habitation", limit=1)

    assert passages
    assert results[0].document_id == document_id
    assert results[0].source == "documents/assurance.pdf"
    assert results[0].metadata == {"document_type": "contrat"}
    assert "Assurance habitation" in results[0].passage


def test_chunk_text_keeps_overlap_between_passages():
    chunks = chunk_text("abcdef", chunk_size=4, overlap=2)

    assert chunks == ["abcd", "cdef"]
