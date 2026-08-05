"""Tests de sûreté des connecteurs d'actifs."""

from app.connectors.assets import (
    BinanceAssetConnector,
    EtoroAssetConnector,
)

READ_ONLY_METHODS = {
    "list_positions",
    "get_balances",
    "get_price_snapshot",
    "sync_history",
}
FORBIDDEN_METHODS = {
    "buy",
    "sell",
    "trade",
    "transfer",
    "withdraw",
    "deposit",
    "place_order",
    "create_order",
    "cancel_order",
}


def public_callables(connector_cls: type) -> set[str]:
    """Retourne les méthodes publiques exposées par une classe de connecteur."""

    return {
        name
        for name in dir(connector_cls)
        if not name.startswith("_") and callable(getattr(connector_cls, name))
    }


def test_asset_connectors_only_expose_read_only_portfolio_methods() -> None:
    """Les squelettes ne doivent exposer aucune opération de trading."""

    for connector_cls in (BinanceAssetConnector, EtoroAssetConnector):
        exposed_methods = public_callables(connector_cls)

        assert READ_ONLY_METHODS.issubset(exposed_methods)
        assert exposed_methods.isdisjoint(FORBIDDEN_METHODS)
