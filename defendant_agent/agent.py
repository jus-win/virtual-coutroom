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

    # ══════════════════════════════════════════════════════════════
    # Dynamic Case Ingestion & Co-Counsel Educational Features
    # ══════════════════════════════════════════════════════════════

    def ingest_new_case(self, raw_case_text: str) -> CaseFile:
        """
        Dynamically ingests case details provided in ANY format (raw narrative,
        FIR copy, bullet points, police report, or JSON), extracts the structured
        schema, saves to SQLite, and updates the active agent state.
        """
        from defendant_agent.case_parser import CaseParser

        parser = CaseParser(llm=self.llm)
        new_case = parser.parse_raw_text(raw_case_text)

        # Save to SQLite
        self.db.save_case(new_case)

        # Update active agent context
        self.case = new_case
        self.case_id = new_case.case_id
        self.state = self.db.get_trial_state(new_case.case_id)
        self._refresh_strategies()

        return new_case

    def get_co_counsel_guidance(
        self,
        incoming_message: Optional[str] = None,
        incoming_speaker: Optional[Speaker | str] = None,
    ) -> Dict[str, Any]:
        """
        When the law student acts as the Defense Counsel, this method acts as their
        Senior Defense Co-Counsel sitting next to them at the defense table:
        Provides stage objectives, statutory grounds, case law citations, and drafted submissions.
        """
        stage = self.state.current_stage

        guidance_map: Dict[TrialStage, Dict[str, Any]] = {
            TrialStage.BAIL_HEARING: {
                "objective": "Secure regular bail for the accused under Section 480 read with Section 479 BNSS 2023.",
                "statutory_grounds": ["Section 480 BNSS (Bail in non-bailable offences)", "Section 479(1) BNSS (1/3 maximum period for first-time offenders)"],
                "precedents": [
                    "Satender Kumar Antil v. CBI (2022) 10 SCC 773 — Bail is the rule, jail is the exception; custody not punitive.",
                    "Phool Kumar v. Delhi Administration (1975) 1 SCC 797 — Section 311 cannot be vicariously fastened to deny bail."
                ],
                "tactical_points": [
                    "Highlight that investigation is complete and chargesheet has been filed.",
                    "Point out that accused is a first-time offender with local family roots and no flight risk.",
                    "Stress that alleged recovery was from an open public space, not personal possession."
                ],
                "suggested_draft": (
                    "May it please this Hon'ble Court. On behalf of the applicant/accused, we submit this application under Section 480 read with Section 479 BNSS 2023. "
                    "The applicant is a first-time offender with no prior criminal antecedents. As settled in Satender Kumar Antil v. CBI (2022), bail is the rule and jail is the exception. "
                    "Investigation is complete, chargesheet is filed, and the alleged recovery was from an open public space. We pray for regular bail on reasonable conditions."
                )
            },
            TrialStage.DISCHARGE_APPLICATION: {
                "objective": "Move for discharge under Section 250 BNSS or dropping of Section 311 / Section 309(4) BNS.",
                "statutory_grounds": ["Section 250 BNSS (Discharge when charge groundless)", "Section 309(1) BNS (Nexus requirement)", "Section 311 BNS (Strict individual liability)"],
                "precedents": [
                    "Sanjay Kumar Rai v. State of UP (2021) — Court is not a mere post office; must examine if allegations disclose grave suspicion.",
                    "Phool Kumar v. Delhi Administration (1975) — Section 311 does not admit vicarious liability.",
                    "Arjun Panditrao Khotkar (2020) — Inadmissibility of electronic records lacking §63(4) BSA certificate."
                ],
                "tactical_points": [
                    "Argue absence of nexus between force and taking.",
                    "Demonstrate that Section 311 is improperly invoked against an unarmed co-accused.",
                    "Challenge admissibility of uncertified CCTV/CDR evidence under Section 63 BSA."
                ],
                "suggested_draft": (
                    "May it please your Honour. The defense moves for discharge under Section 250 BNSS. "
                    "Under Sanjay Kumar Rai (2021), this Court must see whether the record discloses grave suspicion. "
                    "First, the weapon is attributed solely to the co-accused, and Phool Kumar (1975) bars vicarious liability under Section 311 BNS. "
                    "Second, the CCTV lacks mandatory Section 63(4) certification. We pray that the accused be discharged."
                )
            },
            TrialStage.PROSECUTION_EVIDENCE: {
                "objective": "Discredit prosecution witnesses (PWs) and expose procedural violations.",
                "statutory_grounds": ["Section 7 BSA 2023 (Identification facts)", "Rule 34 & 35 Telangana Criminal Rules of Practice, 1990", "Section 23 BSA Proviso (Discovery rule)"],
                "precedents": [
                    "Shaikh Umar Ahmed Shaikh (1998) 5 SCC 103 — Prior exposure of accused vitiates TIP.",
                    "Bodhraj v. State of J&K (2002) 8 SCC 45 — Open place recovery negates exclusive possession."
                ],
                "tactical_points": [
                    "For Complainant (PW1): Question visibility, flickering streetlights, helmet/mask, and prior exposure of photographs at police station.",
                    "For Panch (PW2): Establish that recovery location was open to the public, and probe whether panch is a frequent/stock police witness."
                ],
                "suggested_draft": (
                    "Cross-Examination Questions for Witness in Box:\n"
                    "1. Isn't it true that the crime scene was dark and you only saw the assailant for a few seconds?\n"
                    "2. You admitted the bike rider was wearing a full-face helmet with a tinted visor, did you not?\n"
                    "3. Isn't it a fact that police showed you photographs of the accused before the TIP was conducted?\n"
                    "4. Was the alleged recovery made from an open roadside spot accessible to anyone?"
                )
            },
            TrialStage.FINAL_ARGUMENTS: {
                "objective": "Establish that prosecution failed to prove guilt beyond reasonable doubt and secure acquittal under Section 258 BNSS.",
                "statutory_grounds": ["Section 104 BSA (Burden of proof on prosecution)", "Section 257 BNSS (Final arguments)", "Section 258 BNSS (Acquittal)"],
                "precedents": [
                    "Gireesan Nair v. State of Kerala (2023) — Unsafe dock identification without valid TIP.",
                    "Bodhraj v. State of J&K (2002) — Flawed open recovery.",
                    "Dudh Nath Pandey v. State of UP (1981) — Alibi substantiated by digital records."
                ],
                "tactical_points": [
                    "Synthesize all four pillars: Vitiated TIP, flawed open recovery, digital alibi, and no Section 311 liability.",
                    "Emphasize standard of proof: beyond reasonable doubt, not mere suspicion."
                ],
                "suggested_draft": (
                    "May it please the Hon'ble Sessions Court. Final arguments on behalf of the accused under Section 257 BNSS:\n"
                    "1. The identification is fatally vitiated under Rule 34 Telangana CRoP and Shaikh Umar Ahmed Shaikh.\n"
                    "2. The recovery from an open roadside bush fails the test of Bodhraj (2002).\n"
                    "3. The digital alibi under Section 9 BSA places the accused 3.5 km away.\n"
                    "4. Section 311 cannot be vicariously applied under Phool Kumar.\n"
                    "The prosecution has failed to establish guilt beyond reasonable doubt. We pray for acquittal under Section 258 BNSS."
                )
            }
        }

        fallback = {
            "objective": f"Advocate on behalf of accused at stage: {stage.label()}",
            "statutory_grounds": ["Section 104 BSA 2023 (Burden of Proof)", "BNS 2023", "BNSS 2023"],
            "precedents": ["Satender Kumar Antil (2022)", "Phool Kumar (1975)"],
            "tactical_points": ["Maintain innocence", "Hold prosecution to strict proof"],
            "suggested_draft": "May it please the Hon'ble Court. The defense respectfully submits that the burden rests squarely upon the prosecution under Section 104 BSA 2023."
        }

        return guidance_map.get(stage, fallback)

    def evaluate_student_defense(self, student_submission: str) -> str:
        """
        Evaluates a defense submission written by the student and returns constructive
        pedagogical feedback from the Senior Defense Counsel.
        """
        text_lower = student_submission.lower()
        feedback = []

        # Check for citation of statutes
        has_statute = any(s in text_lower for s in ["bnss", "bns", "bsa", "section", "§", "crpc", "ipc"])
        if has_statute:
            feedback.append("Good job anchoring your submission in statutory provisions.")
        else:
            feedback.append("Recommendation: Always cite specific statutory sections (e.g. Section 480 BNSS for bail, Section 250 BNSS for discharge).")

        # Check for landmark case citations
        precedents_found = []
        for name in ["satender", "antil", "phool kumar", "bodhraj", "shaikh umar", "arjun", "khotkar", "sanjay kumar rai"]:
            if name in text_lower:
                precedents_found.append(name.title())

        if precedents_found:
            feedback.append(f"Strong advocacy citing precedent ({', '.join(precedents_found)}). Judges in Telangana Sessions Courts place heavy reliance on Supreme Court authorities.")
        else:
            feedback.append("Recommendation: Bolster your submission by citing binding Supreme Court precedents (e.g. *Satender Kumar Antil* for bail, *Phool Kumar* against §311 vicarious liability, or *Bodhraj* on open recovery).")

        # Check tone
        if "hon'ble" in text_lower or "may it please" in text_lower or "learned" in text_lower:
            feedback.append("Excellent courtroom etiquette addressing the Bench.")
        else:
            feedback.append("Etiquette Tip: Begin your oral submission with 'May it please your Honour' or 'May it please this Hon'ble Court'.")

        return "\n\n".join(feedback)
