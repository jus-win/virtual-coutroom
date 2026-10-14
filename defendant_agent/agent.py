"""
defendant_agent/agent.py
────────────────────────
Core Defendant AI Agent.
Adheres to the Virtual Courtroom multi-agent integration interface.
Coordinates between SQLite database, strategy analyzer, prompt builder, and LLM provider.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List

from defendant_agent.models import (
    CaseFile,
    TrialStage,
    DefenseVector,
    Speaker,
    AgentState,
    ConversationEntry,
)
from defendant_agent.database import CourtroomDatabase
from defendant_agent.strategy_analyzer import StrategyAnalyzer
from defendant_agent.prompt_builder import CourtroomPromptBuilder
from defendant_agent.llm_provider import BaseLLMProvider, get_llm_provider


class DefendantAgent:
    """
    Defendant AI Agent representing the accused's legal defense in a Virtual Courtroom.
    Designed to integrate into a multi-agent courtroom orchestrator alongside Judge and Prosecutor agents.
    """

    def __init__(
        self,
        case_id: str,
        db: Optional[CourtroomDatabase] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.case_id = case_id
        self.db = db or CourtroomDatabase()
        self.llm = llm_provider or get_llm_provider()

        # Load case from database
        self.case = self.db.load_case(case_id)
        if not self.case:
            raise ValueError(f"Case with ID '{case_id}' was not found in the database.")

        # Load or initialize agent state
        self.state = self.db.get_trial_state(case_id)

        # Run strategy analysis if not already done
        self.strategy_details: Dict[str, Any] = {}
        self._refresh_strategies()

    def _refresh_strategies(self) -> None:
        """Run analysis on case facts to detect applicable defense vectors."""
        analyzer = StrategyAnalyzer(self.case)
        active_vectors, details = analyzer.analyze()
        self.state.active_strategies = active_vectors
        self.strategy_details = details
        self.db.update_trial_state(self.state)

    # ══════════════════════════════════════════════════════════════
    # Public Multi-Agent Framework Interface
    # ══════════════════════════════════════════════════════════════

    def take_turn(
        self,
        incoming_message: Optional[str] = None,
        incoming_speaker: Optional[Speaker | str] = None,
        save_to_history: bool = True,
    ) -> str:
        """
        Primary turn-taking method called by the orchestrator.
        1. Logs the incoming speaker's message (if provided).
        2. Retrieves recent conversation history from SQLite.
        3. Constructs prompt using current stage, active strategies, and case facts.
        4. Calls LLM to generate defense response.
        5. Logs defense response to SQLite.
        6. Returns the response text.
        """
        # 1. Record incoming message if present
        if incoming_message and incoming_speaker and save_to_history:
            speaker_enum = (
                incoming_speaker
                if isinstance(incoming_speaker, Speaker)
                else Speaker(str(incoming_speaker).upper())
            )
            self.db.add_message(
                case_id=self.case_id,
                speaker=speaker_enum,
                message=incoming_message,
                stage=self.state.current_stage,
            )

        # 2. Fetch recent conversation history
        history = self.db.get_conversation_history(self.case_id, limit=20)

        # 3. Build system instruction and user prompt
        system_instruction = CourtroomPromptBuilder.build_system_instruction(
            case=self.case,
            state=self.state,
            active_strategy_details=self.strategy_details,
        )

        user_prompt = CourtroomPromptBuilder.build_user_prompt(
            case=self.case,
            state=self.state,
            conversation_history=history,
            incoming_message=incoming_message,
            incoming_speaker=str(incoming_speaker) if incoming_speaker else None,
        )

        # 4. Generate defense counsel response via LLM
        response_text = self.llm.generate(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        # 5. Record defense response in database
        if save_to_history:
            self.db.add_message(
                case_id=self.case_id,
                speaker=Speaker.DEFENDANT,
                message=response_text,
                stage=self.state.current_stage,
            )

        return response_text

    def advance_stage(self, new_stage: TrialStage | str) -> None:
        """
        Called by orchestrator to transition to a new stage of trial.
        Updates internal state and SQLite trial_state.
        """
        stage_enum = (
            new_stage
            if isinstance(new_stage, TrialStage)
            else TrialStage.from_str(str(new_stage))
        )
        self.state.current_stage = stage_enum
        self.case.current_stage = stage_enum
        self.db.update_trial_state(self.state)

    def set_cross_examination_witness(self, witness_id: Optional[str]) -> None:
        """
        Called when a specific witness enters the witness box for cross-examination.
        E.g. 'PW1', 'PW2'.
        """
        self.state.current_cross_exam_witness = witness_id
        self.db.update_trial_state(self.state)

    def get_status(self) -> Dict[str, Any]:
        """
        Returns metadata for coordinator / dashboard inspection.
        """
        return {
            "case_id": self.case_id,
            "court": self.case.court,
            "accused_name": self.case.accused.name,
            "current_stage": self.state.current_stage.value,
            "current_stage_label": self.state.current_stage.label(),
            "active_strategies": [s.value for s in self.state.active_strategies],
            "current_witness": self.state.current_cross_exam_witness,
            "total_witnesses": len(self.case.witnesses),
            "charges": self.case.charges,
        }

    def generate_defense_brief(self) -> Dict[str, Any]:
        """
        Produces a comprehensive pre-trial defense strategy report
        analyzing prosecution vulnerabilities, statutory defenses, and case law.
        """
        return {
            "case_id": self.case_id,
            "accused": {
                "name": self.case.accused.name,
                "age": self.case.accused.age,
                "first_time_offender": self.case.accused.is_first_time_offender,
                "bail_status": self.case.accused.bail_status,
                "alibi": self.case.accused.alibi_description,
            },
            "charges": self.case.charges,
            "active_vectors": [
                {
                    "vector": s.value,
                    "description": s.description(),
                    "details": self.strategy_details.get(s.value, {}),
                }
                for s in self.state.active_strategies
            ],
            "electronic_vulnerabilities": (
                self.case.evidence.electronic.vulnerabilities()
                if self.case.evidence.electronic
                else []
            ),
            "tip_vulnerabilities": (
                self.case.evidence.tip_report.violations()
                if self.case.evidence.tip_report
                else ["No TIP held"]
            ),
            "recovery_vulnerabilities": (
                self.case.evidence.recovery_mahazar.violations()
                if self.case.evidence.recovery_mahazar
                else []
            ),
        }
