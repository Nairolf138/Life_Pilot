-- Assets and portfolio positions tracked by LifePilot Admin.
-- Target database: PostgreSQL.

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN (
        'cash',
        'stock',
        'etf',
        'crypto',
        'fund',
        'bond',
        'other'
    )),
    symbol TEXT,
    name TEXT NOT NULL,
    quantity NUMERIC(24, 8) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    average_buy_price NUMERIC(18, 6),
    current_price NUMERIC(18, 6),
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    current_value NUMERIC(18, 2),
    pnl_unrealized NUMERIC(18, 2),
    last_price_sync_at TIMESTAMPTZ,
    raw_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (average_buy_price IS NULL OR average_buy_price >= 0),
    CHECK (current_price IS NULL OR current_price >= 0)
);

CREATE INDEX idx_assets_user_id ON assets(user_id);
CREATE INDEX idx_assets_account_id ON assets(account_id);
CREATE INDEX idx_assets_asset_type ON assets(asset_type);
CREATE INDEX idx_assets_symbol ON assets(symbol);
CREATE INDEX idx_assets_currency ON assets(currency);
