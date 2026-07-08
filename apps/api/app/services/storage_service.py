"""Service de stockage privé des fichiers utilisateurs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Annotated, BinaryIO, Protocol
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class StoredFile:
    """Métadonnées calculées et persistées après stockage d'un fichier."""

    file_path: str
    file_hash: str
    mime_type: str | None
    file_size: int


@dataclass(frozen=True, slots=True)
class DownloadedFile:
    """Fichier récupéré depuis un stockage privé après contrôle d'accès métier."""

    content: bytes
    file_path: str
    file_hash: str
    mime_type: str | None
    file_size: int


class StorageBackend(Protocol):
    """Contrat minimal pour une stratégie de stockage de documents privés."""

    def upload_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None,
        file_hash: str,
    ) -> None: ...

    def download_bytes(self, *, object_key: str) -> bytes: ...


class S3StorageBackend:
    """Backend MinIO compatible S3 via boto3."""

    def __init__(self, settings: Settings) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - dépend de l'environnement
            raise RuntimeError(
                "La dépendance boto3 est requise pour le stockage MinIO/S3."
            ) from exc

        self._bucket = settings.storage_s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_s3_endpoint_url,
            aws_access_key_id=settings.storage_s3_access_key,
            aws_secret_access_key=settings.storage_s3_secret_key,
            region_name=settings.storage_s3_region,
            use_ssl=settings.storage_s3_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    def upload_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None,
        file_hash: str,
    ) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=object_key,
            Body=content,
            ContentType=mime_type or "application/octet-stream",
            Metadata={"file_hash": file_hash},
        )

    def download_bytes(self, *, object_key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=object_key)
        except Exception as exc:  # pragma: no cover - dépend du client S3
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier introuvable dans le stockage.",
            ) from exc
        return response["Body"].read()


class LocalStorageBackend:
    """Backend local réservé aux développements et tests."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def upload_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None,
        file_hash: str,
    ) -> None:
        file_path = self._root / object_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    def download_bytes(self, *, object_key: str) -> bytes:
        file_path = self._root / object_key
        if not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier introuvable dans le stockage.",
            )
        return file_path.read_bytes()


class StorageService:
    """Gère les uploads, téléchargements et métadonnées des documents privés."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._backend = self._build_backend(settings)

    async def upload_document_file(
        self,
        *,
        user_id: UUID,
        document_type: str,
        file: UploadFile,
    ) -> StoredFile:
        """Stocke un document et calcule ses métadonnées."""

        content = await file.read()
        return self.upload_document_bytes(
            user_id=user_id,
            document_type=document_type,
            filename=file.filename,
            content=content,
            mime_type=file.content_type,
        )

    def upload_document_bytes(
        self,
        *,
        user_id: UUID,
        document_type: str,
        filename: str | None,
        content: bytes,
        mime_type: str | None,
    ) -> StoredFile:
        """Stocke un contenu déjà lu et retourne ses métadonnées."""

        file_hash = self.calculate_file_hash(content)
        normalized_mime_type = mime_type or "application/octet-stream"
        object_key = self.build_document_path(
            user_id=user_id,
            document_type=document_type,
            filename=filename,
        )
        self._backend.upload_bytes(
            object_key=object_key,
            content=content,
            mime_type=normalized_mime_type,
            file_hash=file_hash,
        )
        return StoredFile(
            file_path=object_key,
            file_hash=file_hash,
            mime_type=normalized_mime_type,
            file_size=len(content),
        )

    def download_document_file(
        self,
        *,
        user_id: UUID,
        document_type: str,
        file_path: str,
        file_hash: str,
        mime_type: str | None,
    ) -> DownloadedFile:
        """Télécharge un fichier après validation du contexte utilisateur."""

        self._ensure_authorized_path(
            user_id=user_id,
            document_type=document_type,
            file_path=file_path,
        )
        content = self._backend.download_bytes(object_key=file_path)
        downloaded_hash = self.calculate_file_hash(content)
        if downloaded_hash != file_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Le hash du fichier stocké ne correspond pas au document.",
            )
        return DownloadedFile(
            content=content,
            file_path=file_path,
            file_hash=downloaded_hash,
            mime_type=mime_type,
            file_size=len(content),
        )

    @staticmethod
    def calculate_file_hash(content: bytes | BinaryIO) -> str:
        """Calcule le SHA-256 du contenu binaire fourni."""

        digest = sha256()
        if isinstance(content, bytes):
            digest.update(content)
        else:
            for chunk in iter(lambda: content.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def build_document_path(
        *,
        user_id: UUID,
        document_type: str,
        filename: str | None,
    ) -> str:
        """Construit un chemin objet logique par utilisateur et type de document."""

        safe_type = _safe_path_segment(document_type)
        safe_name = Path(filename or "document").name
        return f"users/{user_id}/documents/{safe_type}/{uuid4()}-{safe_name}"

    def _ensure_authorized_path(
        self,
        *,
        user_id: UUID,
        document_type: str,
        file_path: str,
    ) -> None:
        safe_type = _safe_path_segment(document_type)
        expected_prefix = f"users/{user_id}/documents/{safe_type}/"
        if not file_path.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès au fichier refusé.",
            )

    @staticmethod
    def _build_backend(settings: Settings) -> StorageBackend:
        if settings.storage_backend == "s3":
            return S3StorageBackend(settings)
        return LocalStorageBackend(Path(settings.storage_local_root))


def _safe_path_segment(value: str) -> str:
    segment = "".join(character if character.isalnum() else "-" for character in value)
    segment = "-".join(part for part in segment.split("-") if part)
    return segment.lower() or "unknown"


async def get_storage_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StorageService:
    """Construit le service de stockage pour FastAPI."""

    return StorageService(settings)
