-- F1 Tracker - Script de création PostgreSQL
-- À exécuter une seule fois pour créer les tables

-- Sessions (chaque GP + type de session)
CREATE TABLE IF NOT EXISTS sessions (
    id          SERIAL PRIMARY KEY,
    year        INTEGER NOT NULL,
    circuit     VARCHAR(100) NOT NULL,
    country     VARCHAR(100),
    session     VARCHAR(10) NOT NULL,  -- R, Q, FP1, FP2, FP3, S, SQ
    date        DATE,
    UNIQUE(year, circuit, session)
);

-- Pilotes (par session car équipe/couleur peut changer)
CREATE TABLE IF NOT EXISTS drivers (
    id          SERIAL PRIMARY KEY,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    code        VARCHAR(4) NOT NULL,   -- VER, HAM, etc.
    full_name   VARCHAR(100),
    team        VARCHAR(100),
    team_color  VARCHAR(7),            -- #hex
    UNIQUE(session_id, code)
);

-- Tours
CREATE TABLE IF NOT EXISTS laps (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    driver_code     VARCHAR(4) NOT NULL,
    lap_number      INTEGER NOT NULL,
    lap_time_ms     INTEGER,           -- en millisecondes
    compound        VARCHAR(20),       -- SOFT, MEDIUM, HARD, etc.
    tyre_life       INTEGER,           -- âge du pneu en tours
    is_valid        BOOLEAN DEFAULT TRUE,
    pit_in          BOOLEAN DEFAULT FALSE,
    pit_out         BOOLEAN DEFAULT FALSE,
    UNIQUE(session_id, driver_code, lap_number)
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_laps_session ON laps(session_id);
CREATE INDEX IF NOT EXISTS idx_laps_driver ON laps(driver_code);
CREATE INDEX IF NOT EXISTS idx_sessions_year ON sessions(year);