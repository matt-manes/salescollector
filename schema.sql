CREATE TABLE
    IF NOT EXISTS states (state TEXT PRIMARY KEY, code_verifier TEXT UNIQUE, date_added TIMESTAMP);

CREATE TABLE
    IF NOT EXISTS shops (shop_id INTEGER PRIMARY KEY, date_added TIMESTAMP);

CREATE TABLE
    IF NOT EXISTS sales (
        listing_id INTEGER,
        product_id INTEGER,
        receipt_id INTEGER,
        transaction_id INTEGER,
        shop_id INTEGER REFERENCES shops (shop_id) ON DELETE RESTRICT,
        title TEXT,
        unit_price REAL,
        quantity INTEGER,
        total_price REAL,
        sale_date TIMESTAMP,
        date_added TIMESTAMP
    );