-- ============================================================
-- Virtual Courtroom — SQLite Database Schema
-- Covers: Cases, Accused, Witnesses, Evidence, Conversations, Trial State
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ── Core Case Metadata ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cases (
    id                  TEXT PRIMARY KEY,          -- e.g. "SC/001/2025"
    court               TEXT NOT NULL,
    judge               TEXT,
    prosecution         TEXT,
    hearing_date        TEXT,
    current_stage       TEXT NOT NULL DEFAULT 'pre_trial',
    -- FIR details
    fir_number          TEXT,
    fir_station         TEXT,
    fir_date            TEXT,
    fir_time            TEXT,
    fir_complainant     TEXT,
    fir_content         TEXT,
    -- Chargesheet
    chargesheet_date    TEXT,
    chargesheet_content TEXT,
    charges             TEXT NOT NULL DEFAULT '[]',  -- JSON array: ["BNS §309(4)", ...]
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Accused Persons ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accused (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id                 TEXT NOT NULL,
    name                    TEXT NOT NULL,
    age                     INTEGER,
    address                 TEXT,
    bail_status             TEXT NOT NULL DEFAULT 'in_custody',
    prior_convictions       TEXT NOT NULL DEFAULT '[]',    -- JSON array of strings
    alibi_description       TEXT,
    is_first_time_offender  INTEGER NOT NULL DEFAULT 1,    -- 0/1 boolean
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- ── Prosecution Witnesses ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS witnesses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id         TEXT NOT NULL,
    witness_id      TEXT NOT NULL,   -- "PW1", "PW2", ...
    name            TEXT NOT NULL,
    witness_type    TEXT NOT NULL,   -- complainant | panch | IO | forensic | TIP_magistrate
    statement_s180  TEXT,            -- §180 BNSS (old §161 CrPC) statement
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- ── Evidence Items (all types) ────────────────────────────────
-- evidence_type: property | TIP_report | FSL_report | CCTV | CDR | recovery_mahazar
-- metadata: JSON object with type-specific fields
CREATE TABLE IF NOT EXISTS evidence_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id         TEXT NOT NULL,
    evidence_type   TEXT NOT NULL,
    exhibit_id      TEXT,            -- "M.O.1", "Ex.P1", etc.
    description     TEXT,
    metadata        TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- ── Conversation History ──────────────────────────────────────
-- Records every utterance from all speakers during the simulation
-- speaker: JUDGE | PROSECUTOR | DEFENDANT | STUDENT | SYSTEM
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     TEXT NOT NULL,
    speaker     TEXT NOT NULL,
    message     TEXT NOT NULL,
    stage       TEXT NOT NULL,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- ── Trial State ───────────────────────────────────────────────
-- One row per case; updated as trial progresses
CREATE TABLE IF NOT EXISTS trial_state (
    case_id                     TEXT PRIMARY KEY,
    current_stage               TEXT NOT NULL DEFAULT 'pre_trial',
    active_strategies           TEXT NOT NULL DEFAULT '[]',   -- JSON: ["tip_attack", ...]
    current_cross_exam_witness  TEXT,                         -- e.g. "PW1"
    strategy_notes              TEXT NOT NULL DEFAULT '{}',   -- JSON: {vector: notes}
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_conv_case_id    ON conversations(case_id);
CREATE INDEX IF NOT EXISTS idx_conv_timestamp  ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_wit_case_id     ON witnesses(case_id);
CREATE INDEX IF NOT EXISTS idx_evi_case_id     ON evidence_items(case_id);
CREATE INDEX IF NOT EXISTS idx_accused_case_id ON accused(case_id);
