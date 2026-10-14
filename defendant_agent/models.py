"""
defendant_agent/models.py
─────────────────────────
Dataclasses and enums representing every domain object in the virtual courtroom:
Case files, accused persons, witnesses, evidence items, trial stage, and defense vectors.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


# ══════════════════════════════════════════════════════════════
# Enumerations
# ══════════════════════════════════════════════════════════════

class TrialStage(str, Enum):
    """
    The 9 stages of a Sessions Court robbery trial under BNSS 2023.
    The orchestrator updates this as the session progresses.
    """
    PRE_TRIAL               = "pre_trial"
    BAIL_HEARING            = "bail_hearing"
    COMMITTAL               = "committal"
    DISCHARGE_APPLICATION   = "discharge_application"
    CHARGE_FRAMING          = "charge_framing"
    PROSECUTION_EVIDENCE    = "prosecution_evidence"
    SECTION_351_EXAMINATION = "section_351_examination"
    DEFENSE_EVIDENCE        = "defense_evidence"
    FINAL_ARGUMENTS         = "final_arguments"
    JUDGMENT                = "judgment"

    @classmethod
    def from_str(cls, value: str) -> "TrialStage":
        try:
            return cls(value)
        except ValueError:
            return cls.PRE_TRIAL

    def label(self) -> str:
        labels = {
            "pre_trial":               "Pre-Trial",
            "bail_hearing":            "Bail Hearing",
            "committal":               "Committal to Sessions",
            "discharge_application":   "Discharge Application (§250 BNSS)",
            "charge_framing":          "Framing of Charges (§251 BNSS)",
            "prosecution_evidence":    "Prosecution Evidence (§253–254 BNSS)",
            "section_351_examination": "§351 Examination of Accused",
            "defense_evidence":        "Defense Evidence (§256 BNSS)",
            "final_arguments":         "Final Arguments (§257 BNSS)",
            "judgment":                "Judgment (§258 BNSS)",
        }
        return labels.get(self.value, self.value)


class DefenseVector(str, Enum):
    """
    The 8 core defense strategy vectors for robbery cases.
    Auto-detected by strategy_analyzer based on case facts.
    """
    NEXUS_ATTACK            = "nexus_attack"            # Force not used "for that end"
    BONA_FIDE_CLAIM         = "bona_fide_claim"         # Honest belief of ownership
    INDIVIDUAL_LIABILITY    = "individual_liability"    # §311 — unarmed co-accused
    DEADLY_WEAPON_REBUTTAL  = "deadly_weapon_rebuttal"  # Object is not a deadly weapon
    TIP_ATTACK              = "tip_attack"              # TIP violated CRoP Rule 34
    RECOVERY_ATTACK         = "recovery_attack"         # Mahazar flawed / open place
    ALIBI                   = "alibi"                   # Accused elsewhere (§9 BSA)
    PRESUMPTION_REBUTTAL    = "presumption_rebuttal"    # §119 BSA — delayed/open recovery

    def description(self) -> str:
        descs = {
            "nexus_attack":           "Force not used 'for that end' — not robbery",
            "bona_fide_claim":        "Bona fide claim of right — no dishonest intent",
            "individual_liability":   "§311 individual liability — unarmed co-accused not liable",
            "deadly_weapon_rebuttal": "Object does not qualify as 'deadly weapon'",
            "tip_attack":             "TIP violated CRoP Rule 34 — identification unsafe",
            "recovery_attack":        "Recovery mahazar flawed — open place / stock witnesses",
            "alibi":                  "Alibi — accused was elsewhere (§9 BSA)",
            "presumption_rebuttal":   "§119 BSA presumption rebutted — delayed/accessible recovery",
        }
        return descs.get(self.value, self.value)


class Speaker(str, Enum):
    """Who sent a message in the courtroom chat."""
    JUDGE               = "JUDGE"
    PROSECUTOR          = "PROSECUTOR"
    DEFENDANT           = "DEFENDANT"
    STUDENT_PROSECUTOR  = "STUDENT_PROSECUTOR"
    STUDENT_DEFENSE     = "STUDENT_DEFENSE"
    SYSTEM              = "SYSTEM"


# ══════════════════════════════════════════════════════════════
# Evidence Sub-Models
# ══════════════════════════════════════════════════════════════

@dataclass
class TIPReport:
    """Test Identification Parade report — CRoP Rule 34."""
    conducted: bool                             = False
    conducted_by: Optional[str]                 = None   # Magistrate name
    date: Optional[str]                         = None
    identified_by: List[str]                    = field(default_factory=list)  # PW IDs
    dummy_match: bool                           = True   # Age/height/complexion match
    witnesses_isolated: bool                    = True
    prior_exposure: bool                        = False  # Accused shown before TIP
    delay_days: int                             = 0      # Days from arrest to TIP

    def violations(self) -> List[str]:
        """Return list of CRoP Rule 34 violations found."""
        v = []
        if not self.conducted:
            v.append("No TIP conducted (dock identification of stranger is unsafe)")
        if self.prior_exposure:
            v.append("Prior exposure of accused to witnesses vitiates TIP (Shaikh Umar Ahmed Shaikh)")
        if not self.witnesses_isolated:
            v.append("Witnesses were not isolated from each other (Rule 34 violation)")
        if not self.dummy_match:
            v.append("Dummy participants did not match accused in age/height/complexion")
        if self.delay_days > 14:
            v.append(f"TIP conducted after {self.delay_days} days delay (Gireesan Nair)")
        return v


@dataclass
class RecoveryMahazar:
    """Recovery panchnama / mahazar details — §23 BSA Proviso + CRoP Rule 35."""
    conducted: bool                             = False
    location: Optional[str]                    = None
    location_type: str                         = "open"   # "open" | "private" | "locked"
    panch_witnesses: List[str]                 = field(default_factory=list)
    stock_witnesses: bool                      = False    # Panches are frequent PS witnesses
    property_tip_in_court: bool               = False    # Rule 35 property identification in Magistrate's court
    recovery_date: Optional[str]              = None
    incident_date: Optional[str]              = None
    signed_at_police_station: bool            = False    # Panchnama signed at PS, not scene

    def violations(self) -> List[str]:
        """Return list of recovery/mahazar infirmities."""
        v = []
        if self.location_type == "open":
            v.append("Recovery from open/public place — no exclusive possession (Bodhraj v. State of J&K)")
        if self.stock_witnesses:
            v.append("Stock panch witnesses — frequent witnesses for same police station")
        if not self.property_tip_in_court:
            v.append("Property TIP not held in Magistrate's court (CRoP Rule 35 violation)")
        if self.signed_at_police_station:
            v.append("Panchnama signed at police station, not at scene of recovery")
        return v


@dataclass
class ElectronicEvidence:
    """CCTV / CDR / Computer output — §63 BSA (replaces §65B IEA)."""
    cctv_present: bool                  = False
    cctv_s63_certificate: bool         = False
    cctv_hash_value: Optional[str]     = None
    cctv_description: Optional[str]    = None
    cdr_present: bool                  = False
    cdr_s63_certificate: bool          = False
    cdr_tower_location: Optional[str]  = None  # Tower location at time of offence

    def cctv_admissible(self) -> bool:
        return self.cctv_present and self.cctv_s63_certificate and bool(self.cctv_hash_value)

    def cdr_admissible(self) -> bool:
        return self.cdr_present and self.cdr_s63_certificate

    def vulnerabilities(self) -> List[str]:
        v = []
        if self.cctv_present and not self.cctv_s63_certificate:
            v.append("CCTV footage lacks mandatory §63(4) BSA certificate — inadmissible (Arjun Panditrao Khotkar)")
        if self.cctv_present and not self.cctv_hash_value:
            v.append("CCTV footage lacks cryptographic hash value (SHA-256) — integrity unverified")
        if self.cdr_present and not self.cdr_s63_certificate:
            v.append("CDR records lack mandatory §63(4) BSA certificate — inadmissible")
        return v


@dataclass
class Evidence:
    """Complete evidence bundle submitted at the start of the simulation."""
    recovered_property: List[Dict[str, Any]]    = field(default_factory=list)
    tip_report: Optional[TIPReport]             = None
    fsl_report: Optional[Dict[str, Any]]        = None
    electronic: Optional[ElectronicEvidence]    = None
    recovery_mahazar: Optional[RecoveryMahazar] = None


# ══════════════════════════════════════════════════════════════
# Core Domain Models
# ══════════════════════════════════════════════════════════════

@dataclass
class WitnessStatement:
    """A prosecution witness and their §180 BNSS statement."""
    witness_id: str          # "PW1", "PW2", ...
    name: str
    witness_type: str        # complainant | panch | IO | forensic | TIP_magistrate
    statement_s180: str      # Full statement text


@dataclass
class Accused:
    """The accused person being defended."""
    name: str
    age: int
    address: str
    bail_status: str                    = "in_custody"
    prior_convictions: List[str]        = field(default_factory=list)
    alibi_description: Optional[str]    = None
    is_first_time_offender: bool        = True


@dataclass
class CaseFile:
    """
    Complete case file loaded from SQLite at session start.
    This is the immutable source of truth for the simulation.
    """
    case_id: str
    court: str
    fir_number: str
    fir_station: str
    fir_date: str
    fir_time: str
    fir_complainant: str
    fir_content: str
    chargesheet_date: str
    chargesheet_content: str
    charges: List[str]           # ["BNS §309(4)", "BNS §311", ...]
    accused: Accused
    witnesses: List[WitnessStatement]
    evidence: Evidence
    current_stage: TrialStage    = TrialStage.PRE_TRIAL
    judge: Optional[str]         = None
    prosecution: Optional[str]   = None
    hearing_date: Optional[str]  = None

    def has_charge(self, section: str) -> bool:
        """Check if a specific BNS section is charged."""
        return any(section in c for c in self.charges)

    def get_witness_by_id(self, pw_id: str) -> Optional[WitnessStatement]:
        return next((w for w in self.witnesses if w.witness_id == pw_id), None)


@dataclass
class AgentState:
    """
    Runtime state of the Defendant Agent — stored in SQLite trial_state table.
    """
    case_id: str
    current_stage: TrialStage                       = TrialStage.PRE_TRIAL
    active_strategies: List[DefenseVector]          = field(default_factory=list)
    current_cross_exam_witness: Optional[str]       = None  # "PW1", "PW2", ...
    strategy_notes: Dict[str, str]                  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "current_stage": self.current_stage.value,
            "active_strategies": [s.value for s in self.active_strategies],
            "current_cross_exam_witness": self.current_cross_exam_witness,
            "strategy_notes": self.strategy_notes,
        }


@dataclass
class ConversationEntry:
    """A single utterance in the courtroom conversation."""
    speaker: Speaker
    message: str
    stage: TrialStage
    timestamp: Optional[str] = None
    case_id: Optional[str]   = None
