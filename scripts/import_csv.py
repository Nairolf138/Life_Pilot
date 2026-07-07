#!/usr/bin/env python3
"""Importe un CSV bancaire Life Pilot depuis la ligne de commande.

Par défaut, le script convertit le CSV en payload JSON compatible avec
POST /transactions/import. Avec --api-url et --token, il envoie directement le
fichier en multipart à l'API.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

try:
    import httpx
except ImportError:  # pragma: no cover - dépendance optionnelle du script
    httpx = None

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.services.importers.csv_bank_importer import (  # noqa: E402
    CsvBankImporter,
    config_from_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import CSV bancaire Life Pilot")
    parser.add_argument("csv_path", type=Path, help="Chemin du fichier CSV à importer")
    parser.add_argument("--account-id", required=True, type=UUID, help="Compte cible")
    parser.add_argument(
        "--mapping",
        help=(
            "JSON de mapping/config. Exemple: "
            '\'{"booking_date":"Date opération","label_raw":"Libellé",\''
            '\'"amount":"Montant"}\''
        ),
    )
    parser.add_argument(
        "--api-url", help="URL complète de l'API, ex: http://localhost:8000/api/v1"
    )
    parser.add_argument("--token", help="Bearer token pour envoyer à l'API")
    return parser.parse_args()


async def post_to_api(args: argparse.Namespace) -> None:
    if httpx is None:
        raise RuntimeError("Installer httpx pour l'envoi API: pip install httpx")
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    with args.csv_path.open("rb") as csv_file:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{args.api_url.rstrip('/')}/transactions/import",
                headers=headers,
                data={
                    "account_id": str(args.account_id),
                    **({"mapping": args.mapping} if args.mapping else {}),
                },
                files={"file": (args.csv_path.name, csv_file, "text/csv")},
            )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def print_payload(args: argparse.Namespace) -> None:
    config = config_from_json(args.mapping, account_id=args.account_id)
    result = CsvBankImporter(config).parse_path(args.csv_path)
    print(result.request.model_dump_json(indent=2))
    if result.ignored_duplicates:
        print(
            f"Doublons ignorés avant envoi: {result.ignored_duplicates}",
            file=sys.stderr,
        )


def main() -> None:
    args = parse_args()
    if args.api_url:
        asyncio.run(post_to_api(args))
    else:
        print_payload(args)


if __name__ == "__main__":
    main()
