"""
tests/test_defendant_agent.py
─────────────────────────────
Comprehensive automated test suite for the Defendant AI Agent and SQLite database.
Run via:
    python -m unittest tests/test_defendant_agent.py
"""

import os
import unittest
from pathlib import Path

from defendant_agent.models import (
    TrialStage,
    DefenseVector,
    Speaker,
    CaseFile,
)
from defendant_agent.database import CourtroomDatabase
from defendant_agent.strategy_analyzer import StrategyAnalyzer
from defendant_agent.agent import DefendantAgent
from seed_db import seed


TEST_DB_PATH = "test_courtroom.db"


class TestDefendantAgentSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure fresh test database
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        # Seed test database
        cls.case = seed(db_path=TEST_DB_PATH)
        cls.db = CourtroomDatabase(db_path=TEST_DB_PATH)
        cls.agent = DefendantAgent(case_id=cls.case.case_id, db=cls.db)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_01_database_tables_exist(self):
        """Verify all SQLite schema tables were created."""
        conn = self.db.get_connection()
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        self.assertIn("cases", tables)
        self.assertIn("accused", tables)
        self.assertIn("witnesses", tables)
        self.assertIn("evidence_items", tables)
        self.assertIn("conversations", tables)
        self.assertIn("trial_state", tables)

    def test_02_case_loaded_correctly(self):
        """Verify case fields loaded from SQLite match expected robbery details."""
        case = self.db.load_case(self.case.case_id)
        self.assertIsNotNone(case)
        self.assertEqual(case.case_id, "SC/142/2024")
        self.assertEqual(case.accused.name, "Mohd. Farhan")
        self.assertEqual(case.accused.age, 22)
        self.assertTrue(case.accused.is_first_time_offender)
        self.assertEqual(len(case.witnesses), 4)
        self.assertIn("PW1", [w.witness_id for w in case.witnesses])
        self.assertIn("PW2", [w.witness_id for w in case.witnesses])

    def test_03_strategy_analyzer_vectors(self):
        """Verify that StrategyAnalyzer identifies all expected defense vectors."""
        analyzer = StrategyAnalyzer(self.case)
        vectors, details = analyzer.analyze()

        self.assertIn(DefenseVector.TIP_ATTACK, vectors)
        self.assertIn(DefenseVector.RECOVERY_ATTACK, vectors)
        self.assertIn(DefenseVector.INDIVIDUAL_LIABILITY, vectors)
        self.assertIn(DefenseVector.ALIBI, vectors)
        self.assertIn(DefenseVector.PRESUMPTION_REBUTTAL, vectors)
        self.assertIn(DefenseVector.NEXUS_ATTACK, vectors)

        # Check that specific citations exist in details
        self.assertIn("Shaikh Umar Ahmed Shaikh", details[DefenseVector.TIP_ATTACK.value]["knowledge"]["precedent"])
        self.assertIn("Bodhraj", details[DefenseVector.RECOVERY_ATTACK.value]["knowledge"]["precedent"])
        self.assertIn("Phool Kumar", details[DefenseVector.INDIVIDUAL_LIABILITY.value]["knowledge"]["precedent"])

    def test_04_agent_turn_taking_and_logging(self):
        """Verify turn taking executes and logs to SQLite conversations table."""
        self.agent.advance_stage(TrialStage.BAIL_HEARING)
        response = self.agent.take_turn(
            incoming_message="Public Prosecutor opposes bail under Section 311 BNS.",
            incoming_speaker=Speaker.PROSECUTOR,
        )
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 50)
        self.assertIn("Section 480", response)

        # Check conversation history in database
        history = self.db.get_conversation_history(self.case.case_id)
        self.assertTrue(len(history) >= 2)
        last_entry = history[-1]
        self.assertEqual(last_entry.speaker, Speaker.DEFENDANT)

    def test_05_stage_transitions(self):
        """Verify stage transitions update state and persist to database."""
        self.agent.advance_stage(TrialStage.FINAL_ARGUMENTS)
        status = self.agent.get_status()
        self.assertEqual(status["current_stage"], "final_arguments")

        # Verify persisted in SQLite trial_state
        state = self.db.get_trial_state(self.case.case_id)
        self.assertEqual(state.current_stage, TrialStage.FINAL_ARGUMENTS)

    def test_06_orchestrator_integration_api(self):
        """Verify all methods required by the multi-agent orchestrator are functional."""
        status = self.agent.get_status()
        self.assertIn("case_id", status)
        self.assertIn("current_stage", status)
        self.assertIn("active_strategies", status)

        brief = self.agent.generate_defense_brief()
        self.assertIn("case_id", brief)
        self.assertIn("accused", brief)
        self.assertIn("active_vectors", brief)
        self.assertIn("tip_vulnerabilities", brief)
        self.assertIn("recovery_vulnerabilities", brief)
        self.assertIn("electronic_vulnerabilities", brief)

    def test_07_dynamic_case_ingestion(self):
        """Verify arbitrary raw text can be ingested dynamically into SQLite."""
        raw_story = (
            "Complainant Suresh was robbed near DLF Cybercity road at 11 PM by two motorcycle riders. "
            "Pillion rider held an iron pipe. Police arrested Salman next day and recovered the stolen watch "
            "from an open public tea stall. Salman claims he was working at a car garage."
        )
        new_case = self.agent.ingest_new_case(raw_story)
        self.assertIsNotNone(new_case)
        self.assertEqual(self.agent.case_id, new_case.case_id)
        # Check that it's persisted in SQLite
        loaded = self.db.load_case(new_case.case_id)
        self.assertIsNotNone(loaded)
        self.assertTrue(len(loaded.witnesses) >= 2)

    def test_08_co_counsel_guidance_and_evaluation(self):
        """Verify Co-Counsel guidance generation and student defense evaluation."""
        guidance = self.agent.get_co_counsel_guidance()
        self.assertIn("objective", guidance)
        self.assertIn("statutory_grounds", guidance)
        self.assertIn("precedents", guidance)
        self.assertIn("suggested_draft", guidance)

        feedback = self.agent.evaluate_student_defense(
            "May it please your Honour. Under Section 480 BNSS, the accused is entitled to bail as per Satender Kumar Antil."
        )
        self.assertIn("statutory", feedback.lower())
        self.assertIn("precedent", feedback.lower())


if __name__ == "__main__":
    unittest.main()

