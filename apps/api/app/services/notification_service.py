"""Service d'orchestration des notifications sortantes.

Le service centralise les règles de remise par sévérité et les adaptateurs de
canaux utilisés par Life Pilot : email, Telegram, WhatsApp et webhook n8n.
Les appels réseau sont volontairement isolés dans des méthodes dédiées afin de
rester testables sans dépendance à un fournisseur externe.
"""

from __future__ import annotations

import asyncio
import json
import smtplib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings


class NotificationChannel(StrEnum):
    """Canaux de notification sortante supportés."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    N8N_WEBHOOK = "n8n_webhook"


class NotificationType(StrEnum):
    """Types d'évènements métier pouvant déclencher une notification."""

    URGENT_ACTION_REQUIRED = "urgent_action_required"
    UPCOMING_DEADLINE = "upcoming_deadline"
    MISSING_DOCUMENT = "missing_document"
    UNMATCHED_TRANSACTION = "unmatched_transaction"
    BUDGET_DRIFT = "budget_drift"
    SUBSCRIPTION_INCREASE = "subscription_increase"
    CONSENT_EXPIRING = "consent_expiring"
    SYNC_ERROR = "sync_error"
    FISCAL_REVIEW_NEEDED = "fiscal_review_needed"
    VEHICLE_DEADLINE = "vehicle_deadline"


class NotificationSeverity(StrEnum):
    """Niveaux pilotant la cadence d'envoi des notifications."""

    CRITICAL = "critical"
    URGENT = "urgent"
    WARNING = "warning"
    INFO = "info"


class NotificationCadence(StrEnum):
    """Cadences d'application de la politique de notification."""

    IMMEDIATE = "immediate"
    DAILY_UNTIL_ACTION = "daily_until_action"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_DIGEST = "weekly_digest"


@dataclass(frozen=True, slots=True)
class NotificationPolicy:
    """Règle de livraison associée à une sévérité."""

    severity: NotificationSeverity
    cadence: NotificationCadence
    description: str


@dataclass(frozen=True, slots=True)
class NotificationRecipient:
    """Coordonnées optionnelles d'un destinataire selon les canaux choisis."""

    user_id: UUID | None = None
    email: str | None = None
    telegram_chat_id: str | None = None
    whatsapp_phone_number: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """Notification normalisée à remettre à un ou plusieurs canaux."""

    notification_type: NotificationType
    severity: NotificationSeverity
    title: str
    body: str
    recipient: NotificationRecipient
    channels: list[NotificationChannel]
    action_url: str | None = None
    deduplication_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ChannelDeliveryResult:
    """Résultat d'envoi pour un canal."""

    channel: NotificationChannel
    delivered: bool
    detail: str
    status_code: int | None = None


@dataclass(frozen=True, slots=True)
class NotificationDeliveryResult:
    """Résultat agrégé d'une notification multi-canaux."""

    notification_type: NotificationType
    severity: NotificationSeverity
    policy: NotificationPolicy
    channel_results: list[ChannelDeliveryResult]

    @property
    def delivered(self) -> bool:
        """Indique si au moins un canal a accepté la notification."""

        return any(result.delivered for result in self.channel_results)


NOTIFICATION_POLICY: dict[NotificationSeverity, NotificationPolicy] = {
    NotificationSeverity.CRITICAL: NotificationPolicy(
        severity=NotificationSeverity.CRITICAL,
        cadence=NotificationCadence.IMMEDIATE,
        description="Envoi immédiat.",
    ),
    NotificationSeverity.URGENT: NotificationPolicy(
        severity=NotificationSeverity.URGENT,
        cadence=NotificationCadence.DAILY_UNTIL_ACTION,
        description="Envoi quotidien jusqu'à action de l'utilisateur.",
    ),
    NotificationSeverity.WARNING: NotificationPolicy(
        severity=NotificationSeverity.WARNING,
        cadence=NotificationCadence.DAILY_DIGEST,
        description="Regroupement dans le digest quotidien.",
    ),
    NotificationSeverity.INFO: NotificationPolicy(
        severity=NotificationSeverity.INFO,
        cadence=NotificationCadence.WEEKLY_DIGEST,
        description="Regroupement dans le digest hebdomadaire.",
    ),
}


class NotificationService:
    """Remet les notifications selon la politique et les canaux demandés."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def dispatch(
        self, message: NotificationMessage
    ) -> NotificationDeliveryResult:
        """Envoie une notification immédiate ou la prépare pour un digest.

        La méthode retourne la politique appliquée avec le résultat de chaque
        canal. Les cadences non immédiates sont exposées dans le résultat afin
        qu'un ordonnanceur puisse les regrouper avant d'appeler ce service.
        """

        policy = NOTIFICATION_POLICY[message.severity]
        if not message.channels:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Au moins un canal de notification est requis.",
            )

        results = [
            await self._dispatch_channel(channel, message)
            for channel in message.channels
        ]
        return NotificationDeliveryResult(
            notification_type=message.notification_type,
            severity=message.severity,
            policy=policy,
            channel_results=results,
        )

    def policy_for(self, severity: NotificationSeverity) -> NotificationPolicy:
        """Retourne la règle de cadence pour une sévérité donnée."""

        return NOTIFICATION_POLICY[severity]

    async def _dispatch_channel(
        self, channel: NotificationChannel, message: NotificationMessage
    ) -> ChannelDeliveryResult:
        if channel == NotificationChannel.EMAIL:
            return await self._send_email(message)
        if channel == NotificationChannel.TELEGRAM:
            return await self._send_telegram(message)
        if channel == NotificationChannel.WHATSAPP:
            return await self._send_whatsapp(message)
        if channel == NotificationChannel.N8N_WEBHOOK:
            return await self._send_n8n_webhook(message)
        return ChannelDeliveryResult(
            channel=channel,
            delivered=False,
            detail="Canal inconnu.",
        )

    async def _send_email(self, message: NotificationMessage) -> ChannelDeliveryResult:
        recipient = message.recipient.email
        smtp_host = getattr(self._settings, "notification_smtp_host", None)
        sender = getattr(self._settings, "notification_email_from", None)
        if not recipient or not smtp_host or not sender:
            return ChannelDeliveryResult(
                channel=NotificationChannel.EMAIL,
                delivered=False,
                detail="Configuration email incomplète.",
            )

        email = EmailMessage()
        email["From"] = sender
        email["To"] = recipient
        email["Subject"] = message.title
        email.set_content(_format_text_payload(message))

        port = int(getattr(self._settings, "notification_smtp_port", 587))
        username = getattr(self._settings, "notification_smtp_username", None)
        password = getattr(self._settings, "notification_smtp_password", None)
        use_tls = bool(getattr(self._settings, "notification_smtp_use_tls", True))

        try:
            with smtplib.SMTP(smtp_host, port, timeout=10) as smtp:
                if use_tls:
                    smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(email)
        except (OSError, smtplib.SMTPException) as exc:
            return ChannelDeliveryResult(
                channel=NotificationChannel.EMAIL,
                delivered=False,
                detail=f"Erreur SMTP: {exc}",
            )
        return ChannelDeliveryResult(
            channel=NotificationChannel.EMAIL,
            delivered=True,
            detail="Email envoyé.",
        )

    async def _send_telegram(
        self, message: NotificationMessage
    ) -> ChannelDeliveryResult:
        token = getattr(self._settings, "notification_telegram_bot_token", None)
        chat_id = message.recipient.telegram_chat_id
        if not token or not chat_id:
            return ChannelDeliveryResult(
                channel=NotificationChannel.TELEGRAM,
                delivered=False,
                detail="Configuration Telegram incomplète.",
            )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": _format_text_payload(message)}
        return await _post_json(NotificationChannel.TELEGRAM, url, payload)

    async def _send_whatsapp(
        self, message: NotificationMessage
    ) -> ChannelDeliveryResult:
        token = getattr(self._settings, "notification_whatsapp_access_token", None)
        phone_number_id = getattr(
            self._settings, "notification_whatsapp_phone_number_id", None
        )
        recipient = message.recipient.whatsapp_phone_number
        if not token or not phone_number_id or not recipient:
            return ChannelDeliveryResult(
                channel=NotificationChannel.WHATSAPP,
                delivered=False,
                detail="Configuration WhatsApp incomplète.",
            )
        url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": _format_text_payload(message)},
        }
        headers = {"Authorization": f"Bearer {token}"}
        return await _post_json(
            NotificationChannel.WHATSAPP, url, payload, headers=headers
        )

    async def _send_n8n_webhook(
        self, message: NotificationMessage
    ) -> ChannelDeliveryResult:
        url = getattr(self._settings, "notification_n8n_webhook_url", None)
        if not url:
            return ChannelDeliveryResult(
                channel=NotificationChannel.N8N_WEBHOOK,
                delivered=False,
                detail="Configuration webhook n8n incomplète.",
            )
        payload = {
            "type": message.notification_type.value,
            "severity": message.severity.value,
            "title": message.title,
            "body": message.body,
            "recipient": {
                "user_id": (
                    str(message.recipient.user_id)
                    if message.recipient.user_id
                    else None
                ),
                "email": message.recipient.email,
                "telegram_chat_id": message.recipient.telegram_chat_id,
                "whatsapp_phone_number": message.recipient.whatsapp_phone_number,
            },
            "action_url": message.action_url,
            "deduplication_key": message.deduplication_key,
            "metadata": message.metadata,
            "created_at": message.created_at.isoformat(),
        }
        secret = getattr(self._settings, "n8n_internal_secret", None)
        headers = {"X-LifePilot-Secret": secret} if secret else None
        return await _post_json(
            NotificationChannel.N8N_WEBHOOK, url, payload, headers=headers
        )


async def _post_json(
    channel: NotificationChannel,
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
) -> ChannelDeliveryResult:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        status_code = await asyncio.to_thread(_open_status, request)
    except urllib.error.HTTPError as exc:
        return ChannelDeliveryResult(
            channel=channel,
            delivered=False,
            detail=f"Erreur HTTP: {exc.reason}",
            status_code=exc.code,
        )
    except urllib.error.URLError as exc:
        return ChannelDeliveryResult(
            channel=channel,
            delivered=False,
            detail=f"Erreur réseau: {exc.reason}",
        )
    return ChannelDeliveryResult(
        channel=channel,
        delivered=200 <= status_code < 300,
        detail="Webhook accepté." if 200 <= status_code < 300 else "Webhook refusé.",
        status_code=status_code,
    )


def _open_status(request: urllib.request.Request) -> int:
    with urllib.request.urlopen(request, timeout=10) as response:
        return int(response.status)


def _format_text_payload(message: NotificationMessage) -> str:
    lines = [message.title, "", message.body, "", f"Sévérité: {message.severity.value}"]
    if message.action_url:
        lines.extend(["", f"Action: {message.action_url}"])
    return "\n".join(lines)


async def get_notification_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationService:
    """Construit le service de notification pour FastAPI ou les workers."""

    return NotificationService(settings)
