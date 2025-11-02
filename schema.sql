CREATE TABLE
    IF NOT EXISTS states (state TEXT PRIMARY KEY, code_verifier TEXT UNIQUE, date_added TIMESTAMP);