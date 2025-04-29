-- 1. Wallets
CREATE TABLE wallets (
    id SERIAL PRIMARY KEY,
    address TEXT NOT NULL UNIQUE,
    label TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Tokens
CREATE TABLE tokens (
    address TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    name TEXT,
    decimals INT DEFAULT 18
);

-- 3. Transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    wallet_id INT REFERENCES wallets(id) ON DELETE CASCADE,
    token_address TEXT REFERENCES tokens(address),
    amount NUMERIC NOT NULL,
    usd_value NUMERIC,
    tx_type TEXT CHECK (tx_type IN ('buy', 'sell')),
    block_time TIMESTAMPTZ NOT NULL,
    tx_hash TEXT UNIQUE NOT NULL
);

-- 4. Price Snapshots
CREATE TABLE price_snapshots (
    id SERIAL PRIMARY KEY,
    token_address TEXT REFERENCES tokens(address),
    price_usd NUMERIC NOT NULL,
    volume_24h NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Alerts
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    wallet_id INT REFERENCES wallets(id) ON DELETE CASCADE,
    txn_id INT REFERENCES transactions(id) ON DELETE CASCADE,
    price_at_txn NUMERIC,
    enriched_score NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Sentiments (Optional)
CREATE TABLE sentiments (
    id SERIAL PRIMARY KEY,
    token_address TEXT REFERENCES tokens(address),
    score FLOAT CHECK (score BETWEEN -1 AND 1),
    source TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
