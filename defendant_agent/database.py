"""
defendant_agent/database.py
───────────────────────────
SQLite persistence layer for the Virtual Courtroom system.
Handles schema initialization, case loading/saving, conversation transcripts,
and trial state management.
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from defendant_agent.models import (
    CaseFile,
    Accused,
    WitnessStatement,
    Evidence,
    TIPReport,
    RecoveryMahazar,
    ElectronicEvidence,
    TrialStage,
    DefenseVector,
    Speaker,
    ConversationEntry,
    AgentState,
)


DEFAULT_SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


class CourtroomDatabase:
    """Manages SQLite connection and data operations for courtroom cases."""

    def __init__(self, db_path: str = "courtroom.db", schema_path: Optional[str] = None):
        self.db_path = db_path
        self.schema_path = schema_path or str(DEFAULT_SCHEMA_PATH)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Initialize database tables from schema.sql if not exists."""
        schema_file = Path(self.schema_path)
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found at {self.schema_path}")

        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)

    # ─────────────────────────────────────────────────────────────
    # Case Operations
    # ─────────────────────────────────────────────────────────────

    def save_case(self, case: CaseFile) -> None:
        """Insert or replace a full CaseFile into the database."""
        with self.get_connection() as conn:
            # 1. Cases table
            conn.execute(
                """
                INSERT OR REPLACE INTO cases (
                    id, court, judge, prosecution, hearing_date, current_stage,
                    fir_number, fir_station, fir_date, fir_time, fir_complainant,
                    fir_content, chargesheet_date, chargesheet_content, charges
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.case_id,
                    case.court,
                    case.judge,
                    case.prosecution,
                    case.hearing_date,
                    case.current_stage.value,
                    case.fir_number,
                    case.fir_station,
                    case.fir_date,
                    case.fir_time,
                    case.fir_complainant,
                    case.fir_content,
                    case.chargesheet_date,
                    case.chargesheet_content,
                    json.dumps(case.charges),
                ),
            )

            # 2. Accused table
            conn.execute("DELETE FROM accused WHERE case_id = ?", (case.case_id,))
            conn.execute(
                """
                INSERT INTO accused (
                    case_id, name, age, address, bail_status,
                    prior_convictions, alibi_description, is_first_time_offender
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.case_id,
                    case.accused.name,
                    case.accused.age,
                    case.accused.address,
                    case.accused.bail_status,
                    json.dumps(case.accused.prior_convictions),
                    case.accused.alibi_description,
                    1 if case.accused.is_first_time_offender else 0,
                ),
            )

            # 3. Witnesses
            conn.execute("DELETE FROM witnesses WHERE case_id = ?", (case.case_id,))
            for w in case.witnesses:
                conn.execute(
                    """
                    INSERT INTO witnesses (case_id, witness_id, name, witness_type, statement_s180)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (case.case_id, w.witness_id, w.name, w.witness_type, w.statement_s180),
                )

            # 4. Evidence items
            conn.execute("DELETE FROM evidence_items WHERE case_id = ?", (case.case_id,))
            # TIP report
            if case.evidence.tip_report:
                tip = case.evidence.tip_report
                conn.execute(
                    """
                    INSERT INTO evidence_items (case_id, evidence_type, exhibit_id, description, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id,
                        "TIP_report",
                        "Ex.P-TIP",
                        "Test Identification Parade Report",
                        json.dumps({
                            "conducted": tip.conducted,
                            "conducted_by": tip.conducted_by,
                            "date": tip.date,
                            "identified_by": tip.identified_by,
                            "dummy_match": tip.dummy_match,
                            "witnesses_isolated": tip.witnesses_isolated,
                            "prior_exposure": tip.prior_exposure,
                            "delay_days": tip.delay_days,
                        }),
                    ),
                )

            # Recovery Mahazar
            if case.evidence.recovery_mahazar:
                rec = case.evidence.recovery_mahazar
                conn.execute(
                    """
                    INSERT INTO evidence_items (case_id, evidence_type, exhibit_id, description, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id,
                        "recovery_mahazar",
                        "Ex.P-MAHAZAR",
                        "Seizure and Recovery Panchnama",
                        json.dumps({
                            "conducted": rec.conducted,
                            "location": rec.location,
                            "location_type": rec.location_type,
                            "panch_witnesses": rec.panch_witnesses,
                            "stock_witnesses": rec.stock_witnesses,
                            "property_tip_in_court": rec.property_tip_in_court,
                            "recovery_date": rec.recovery_date,
                            "incident_date": rec.incident_date,
                            "signed_at_police_station": rec.signed_at_police_station,
                        }),
                    ),
                )

            # Electronic Evidence
            if case.evidence.electronic:
                ee = case.evidence.electronic
                conn.execute(
                    """
                    INSERT INTO evidence_items (case_id, evidence_type, exhibit_id, description, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id,
                        "electronic",
                        "Ex.P-ELEC",
                        "CCTV and CDR Electronic Records",
                        json.dumps({
                            "cctv_present": ee.cctv_present,
                            "cctv_s63_certificate": ee.cctv_s63_certificate,
                            "cctv_hash_value": ee.cctv_hash_value,
                            "cctv_description": ee.cctv_description,
                            "cdr_present": ee.cdr_present,
                            "cdr_s63_certificate": ee.cdr_s63_certificate,
                            "cdr_tower_location": ee.cdr_tower_location,
                        }),
                    ),
                )

            # Recovered Property items
            for item in case.evidence.recovered_property:
                conn.execute(
                    """
                    INSERT INTO evidence_items (case_id, evidence_type, exhibit_id, description, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id,
                        "property",
                        item.get("exhibit_id", "M.O."),
                        item.get("description", "Seized Property"),
                        json.dumps(item),
                    ),
                )

            # 5. Initialize trial_state if missing
            conn.execute(
                """
                INSERT OR IGNORE INTO trial_state (case_id, current_stage, active_strategies, strategy_notes)
                VALUES (?, ?, ?, ?)
                """,
                (case.case_id, case.current_stage.value, "[]", "{}"),
            )
            conn.commit()

    def load_case(self, case_id: str) -> Optional[CaseFile]:

        """Fetch and reconstruct a CaseFile from database."""
        with self.get_connection() as conn:
            case_row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
            if not case_row:
                return None

            accused_row = conn.execute("SELECT * FROM accused WHERE case_id = ?", (case_id,)).fetchone()
            if not accused_row:
                accused = Accused(name="Unknown", age=25, address="")
            else:
                accused = Accused(
                    name=accused_row["name"],
                    age=accused_row["age"],
                    address=accused_row["address"],
                    bail_status=accused_row["bail_status"],
                    prior_convictions=json.loads(accused_row["prior_convictions"] or "[]"),
                    alibi_description=accused_row["alibi_description"],
                    is_first_time_offender=bool(accused_row["is_first_time_offender"]),
                )

            witness_rows = conn.execute("SELECT * FROM witnesses WHERE case_id = ? ORDER BY id ASC", (case_id,)).fetchall()
            witnesses = [
                WitnessStatement(
                    witness_id=w["witness_id"],
                    name=w["name"],
                    witness_type=w["witness_type"],
                    statement_s180=w["statement_s180"],
                )
                for w in witness_rows
            ]

            evidence_rows = conn.execute("SELECT * FROM evidence_items WHERE case_id = ?", (case_id,)).fetchall()
            tip_report: Optional[TIPReport] = None
            recovery_mahazar: Optional[RecoveryMahazar] = None
            electronic: Optional[ElectronicEvidence] = None
            recovered_property: List[Dict[str, Any]] = []

            for er in evidence_rows:
                etype = er["evidence_type"]
                meta = json.loads(er["metadata"] or "{}")
                if etype == "TIP_report":
                    tip_report = TIPReport(
                        conducted=meta.get("conducted", False),
                        conducted_by=meta.get("conducted_by"),
                        date=meta.get("date"),
                        identified_by=meta.get("identified_by", []),
                        dummy_match=meta.get("dummy_match", True),
                        witnesses_isolated=meta.get("witnesses_isolated", True),
                        prior_exposure=meta.get("prior_exposure", False),
                        delay_days=meta.get("delay_days", 0),
                    )
                elif etype == "recovery_mahazar":
                    recovery_mahazar = RecoveryMahazar(
                        conducted=meta.get("conducted", False),
                        location=meta.get("location"),
                        location_type=meta.get("location_type", "open"),
                        panch_witnesses=meta.get("panch_witnesses", []),
                        stock_witnesses=meta.get("stock_witnesses", False),
                        property_tip_in_court=meta.get("property_tip_in_court", False),
                        recovery_date=meta.get("recovery_date"),
                        incident_date=meta.get("incident_date"),
                        signed_at_police_station=meta.get("signed_at_police_station", False),
                    )
                elif etype == "electronic":
                    electronic = ElectronicEvidence(
                        cctv_present=meta.get("cctv_present", False),
                        cctv_s63_certificate=meta.get("cctv_s63_certificate", False),
                        cctv_hash_value=meta.get("cctv_hash_value"),
                        cctv_description=meta.get("cctv_description"),
                        cdr_present=meta.get("cdr_present", False),
                        cdr_s63_certificate=meta.get("cdr_s63_certificate", False),
                        cdr_tower_location=meta.get("cdr_tower_location"),
                    )
                elif etype == "property":
                    recovered_property.append(meta)

            evidence = Evidence(
                recovered_property=recovered_property,
                tip_report=tip_report,
                fsl_report=None,
                electronic=electronic,
                recovery_mahazar=recovery_mahazar,
            )

            charges = json.loads(case_row["charges"] or "[]")

            return CaseFile(
                case_id=case_row["id"],
                court=case_row["court"],
                judge=case_row["judge"],
                prosecution=case_row["prosecution"],
                hearing_date=case_row["hearing_date"],
                current_stage=TrialStage.from_str(case_row["current_stage"]),
                fir_number=case_row["fir_number"],
                fir_station=case_row["fir_station"],
                fir_date=case_row["fir_date"],
                fir_time=case_row["fir_time"],
                fir_complainant=case_row["fir_complainant"],
                fir_content=case_row["fir_content"],
                chargesheet_date=case_row["chargesheet_date"],
                chargesheet_content=case_row["chargesheet_content"],
                charges=charges,
                accused=accused,
                witnesses=witnesses,
                evidence=evidence,
            )

    # ─────────────────────────────────────────────────────────────
    # Conversation History
    # ─────────────────────────────────────────────────────────────

    def add_message(
        self, case_id: str, speaker: Speaker, message: str, stage: TrialStage
    ) -> int:
        """Log a message to the conversation history and return the inserted row id."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (case_id, speaker, message, stage)
                VALUES (?, ?, ?, ?)
                """,
                (case_id, speaker.value, message, stage.value),
            )
            last_id = cursor.lastrowid
            conn.commit()
            return last_id


    def get_conversation_history(
        self, case_id: str, limit: int = 50
    ) -> List[ConversationEntry]:
        """Fetch chronological recent conversation entries."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT speaker, message, stage, timestamp, case_id
                FROM conversations
                WHERE case_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()

            return [
                ConversationEntry(
                    speaker=Speaker(r["speaker"]),
                    message=r["message"],
                    stage=TrialStage.from_str(r["stage"]),
                    timestamp=r["timestamp"],
                    case_id=r["case_id"],
                )
                for r in rows
            ]

    # ─────────────────────────────────────────────────────────────
    # Trial State Operations
    # ─────────────────────────────────────────────────────────────

    def get_trial_state(self, case_id: str) -> AgentState:
        """Retrieve the current AgentState for a case."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM trial_state WHERE case_id = ?", (case_id,)
            ).fetchone()
            if not row:
                return AgentState(case_id=case_id)

            active_strategies = [
                DefenseVector(s) for s in json.loads(row["active_strategies"] or "[]")
                if s in [e.value for e in DefenseVector]
            ]
            notes = json.loads(row["strategy_notes"] or "{}")

            return AgentState(
                case_id=case_id,
                current_stage=TrialStage.from_str(row["current_stage"]),
                active_strategies=active_strategies,
                current_cross_exam_witness=row["current_cross_exam_witness"],
                strategy_notes=notes,
            )

    def update_trial_state(self, state: AgentState) -> None:
        """Save updated AgentState back to SQLite."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO trial_state (
                    case_id, current_stage, active_strategies,
                    current_cross_exam_witness, strategy_notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    state.case_id,
                    state.current_stage.value,
                    json.dumps([s.value for s in state.active_strategies]),
                    state.current_cross_exam_witness,
                    json.dumps(state.strategy_notes),
                ),
            )
            # Also update current_stage on the case table
            conn.execute(
                "UPDATE cases SET current_stage = ? WHERE id = ?",
                (state.current_stage.value, state.case_id),
            )
            conn.commit()

