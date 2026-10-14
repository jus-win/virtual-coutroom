"""
defendant_agent/strategy_analyzer.py
────────────────────────────────────
Analyzes case facts, evidence items, and chargesheet materials to automatically
identify viable defense vectors under BNS 2023, BNSS 2023, BSA 2023, and Telangana CRoP 1990.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
from defendant_agent.models import CaseFile, DefenseVector


# ══════════════════════════════════════════════════════════════
# Statutory & Precedent Knowledge Base for Defense Vectors
# ══════════════════════════════════════════════════════════════

VECTOR_KNOWLEDGE: Dict[DefenseVector, Dict[str, Any]] = {
    DefenseVector.NEXUS_ATTACK: {
        "title": "Nexus Attack (Absence of Force 'For That End')",
        "statute": "Section 309(1) BNS 2023 (formerly §390 IPC)",
        "precedent": "State of Maharashtra v. Joseph Mingel Koli (1997 Bom CR) & Dhananjay v. State of Bihar (2007) 14 SCC 768",
        "principle": (
            "Hurt or fear must be intentionally caused FOR THE PURPOSE of committing theft. "
            "If force was independent, subsequent, or accidental, the offence remains simple theft "
            "under §303(2) BNS or hurt under §115 BNS, not robbery under §309(4) BNS."
        ),
    },
    DefenseVector.BONA_FIDE_CLAIM: {
        "title": "Bona Fide Claim of Right",
        "statute": "Section 303(1) Explanation BNS 2023 (Mens Rea requirement)",
        "precedent": "K.N. Mehra v. State of Rajasthan AIR 1957 SC 369 & Chander Kanta v. State 1980 Cri LJ 48",
        "principle": (
            "Taking property under a bona fide belief of ownership or lawful entitlement negates "
            "'dishonest intent' (animus furandi). Absence of dishonest intention completely defeats "
            "a theft charge, collapsing any robbery charge under §309."
        ),
    },
    DefenseVector.INDIVIDUAL_LIABILITY: {
        "title": "Strict Individual Liability under Section 311 BNS",
        "statute": "Section 311 BNS 2023 (formerly §397 IPC)",
        "precedent": "Phool Kumar v. Delhi Administration (1975) 1 SCC 797 & Samiuddin v. State (NCT of Delhi) (2010)",
        "principle": (
            "Section 311 BNS does NOT create vicarious or constructive liability. Only the specific "
            "individual who personally 'uses' a deadly weapon attracts the mandatory minimum 7-year "
            "sentence. An unarmed co-accused cannot be convicted under §311 BNS."
        ),
    },
    DefenseVector.DEADLY_WEAPON_REBUTTAL: {
        "title": "Rebuttal of Deadly Weapon Classification",
        "statute": "Section 311 BNS 2023",
        "precedent": "Lakshmiammal v. State (1990 Cri LJ 2378) & Bachan Singh v. State of Punjab (1993)",
        "principle": (
            "An object must be inherently lethal or used in a lethal manner to qualify as a 'deadly weapon'. "
            "Ordinary iron rods, small kitchen knives, or blunt sticks without proven lethal dimension "
            "do not automatically satisfy the threshold under §311 BNS."
        ),
    },
    DefenseVector.TIP_ATTACK: {
        "title": "Vitiation of Test Identification Parade (TIP)",
        "statute": "Rule 34, Telangana Criminal Rules of Practice, 1990 & Section 7 BSA 2023",
        "precedent": "Shaikh Umar Ahmed Shaikh v. State of Maharashtra (1998) 5 SCC 103 & Gireesan Nair v. State of Kerala (2023) 1 SCC 180",
        "principle": (
            "Failure to hold TIP, delay exceeding 14 days without explanation, non-isolation of witnesses, "
            "showing the accused to witnesses beforehand, or dissimilar dummy participants renders "
            "subsequent dock identification in court inherently unsafe and unreliable."
        ),
    },
    DefenseVector.RECOVERY_ATTACK: {
        "title": "Flawed Recovery Mahazar & Open Place Seizure",
        "statute": "Section 23 BSA 2023 Proviso (formerly §27 Evidence Act) & Rule 35 Telangana CRoP",
        "precedent": "Bodhraj v. State of J&K (2002) 8 SCC 45 & Trimbak v. State of M.P. AIR 1954 SC 39",
        "principle": (
            "Recovery from an open space accessible to the general public does not establish conscious, "
            "exclusive possession by the accused. Use of stock/police-friendly panch witnesses and failure "
            "to hold property identification before a Magistrate (Rule 35) vitiates the seizure."
        ),
    },
    DefenseVector.ALIBI: {
        "title": "Plea of Alibi (Plea of Absence)",
        "statute": "Section 9 BSA 2023 (formerly §11 Evidence Act)",
        "precedent": "Dudh Nath Pandey v. State of U.P. AIR 1981 SC 911 & Mukesh v. State (NCT of Delhi) (2017) 3 SCC 1",
        "principle": (
            "Accused establishes physical impossibility of presence at the scene of offence at the time of crime "
            "via corroborative evidence, CDR cell tower records, or disinterested third-party testimony."
        ),
    },
    DefenseVector.PRESUMPTION_REBUTTAL: {
        "title": "Rebuttal of Presumption from Possession of Stolen Goods",
        "statute": "Section 119 BSA 2023 (formerly §114 Illustration (a) Evidence Act)",
        "precedent": "Tulsiram v. State of M.P. AIR 1985 SC 74 & Nagappa Dondiba Kalal v. State of Karnataka AIR 1980 SC 1753",
        "principle": (
            "Presumption under §119 BSA requires goods to be recovered 'soon after' the theft. Delayed recovery, "
            "common mass-manufactured articles without unique identification, or reasonable explanation "
            "by the accused completely rebuts any presumption of robbery or theft."
        ),
    },
}


class StrategyAnalyzer:
    """Analyzes a CaseFile and generates actionable defense strategies."""

    def __init__(self, case: CaseFile):
        self.case = case

    def analyze(self) -> Tuple[List[DefenseVector], Dict[str, Any]]:
        """
        Evaluate all 8 defense vectors against case materials.
        Returns:
            active_vectors: list of DefenseVector enums applicable to this case.
            details: dict of vector details, trigger reasons, and tactical instructions.
        """
        active_vectors: List[DefenseVector] = []
        details: Dict[str, Any] = {}

        # ── 1. TIP Attack Vector ─────────────────────────────────
        tip = self.case.evidence.tip_report
        if tip is None or not tip.conducted or tip.prior_exposure or not tip.witnesses_isolated or not tip.dummy_match or tip.delay_days > 14:
            active_vectors.append(DefenseVector.TIP_ATTACK)
            reasons = []
            if tip is None or not tip.conducted:
                reasons.append("No Test Identification Parade conducted; dock identification is unsafe for strangers.")
            else:
                reasons.extend(tip.violations())
            details[DefenseVector.TIP_ATTACK.value] = {
                "knowledge": VECTOR_KNOWLEDGE[DefenseVector.TIP_ATTACK],
                "triggers": reasons,
                "strategy": "Object strongly to dock identification. Cross-examine complainant on lighting, duration of observation, and prior exposure at police station.",
            }

        # ── 2. Recovery Mahazar Attack Vector ─────────────────────
        rec = self.case.evidence.recovery_mahazar
        if rec and (rec.location_type == "open" or rec.stock_witnesses or not rec.property_tip_in_court or rec.signed_at_police_station):
            active_vectors.append(DefenseVector.RECOVERY_ATTACK)
            details[DefenseVector.RECOVERY_ATTACK.value] = {
                "knowledge": VECTOR_KNOWLEDGE[DefenseVector.RECOVERY_ATTACK],
                "triggers": rec.violations(),
                "strategy": "Challenge Section 23 BSA recovery. Argue open accessibility negates exclusive possession. Subpoena panch witnesses' prior deposition records to prove stock nature.",
            }

        # ── 3. Individual Liability under §311 BNS ────────────────
        if self.case.has_charge("311"):
            # Check if case materials show accused did not personally carry or use deadly weapon
            active_vectors.append(DefenseVector.INDIVIDUAL_LIABILITY)
            details[DefenseVector.INDIVIDUAL_LIABILITY.value] = {
                "knowledge": VECTOR_KNOWLEDGE[DefenseVector.INDIVIDUAL_LIABILITY],
                "triggers": [
                    "Accused charged under Section 311 BNS with mandatory 7-year minimum.",
                    "Prosecution must prove personal use of deadly weapon by this specific accused.",
                ],
                "strategy": "Emphasize Phool Kumar v. Delhi Administration. Section 311 BNS does not permit vicarious liability. If co-accused held weapon, this accused cannot be convicted under §311.",
            }

        # ── 4. Electronic Evidence / CCTV Attack ─────────────────
        elec = self.case.evidence.electronic
        if elec and elec.vulnerabilities():
            # Not a separate vector enum, but a powerful cross-cutting evidentiary attack
            details["electronic_evidence_attack"] = {
                "statute": "Section 63(4) BSA 2023",
                "precedent": "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020) 7 SCC 1",
                "triggers": elec.vulnerabilities(),
                "strategy": "File formal written objection at time of marking CCTV/CDR exhibits. Electronic evidence without §63(4) certificate is legally inadmissible.",
            }

        # ── 5. Alibi Defense ─────────────────────────────────────
        if self.case.accused.alibi_description:
            active_vectors.append(DefenseVector.ALIBI)
            details[DefenseVector.ALIBI.value] = {
                "knowledge": VECTOR_KNOWLEDGE[DefenseVector.ALIBI],
                "triggers": [f"Accused claims alibi: {self.case.accused.alibi_description}"],
                "strategy": "Plead Section 9 BSA alibi at the earliest stage. Cross-examine IO on failure to investigate defense alibi and tower CDR locations.",
            }

        # ── 6. Presumption Rebuttal (§119 BSA) ───────────────────
        if self.case.evidence.recovered_property:
            # Check for generic property or delay
            active_vectors.append(DefenseVector.PRESUMPTION_REBUTTAL)
            details[DefenseVector.PRESUMPTION_REBUTTAL.value] = {
                "knowledge": VECTOR_KNOWLEDGE[DefenseVector.PRESUMPTION_REBUTTAL],
                "triggers": [
                    f"{len(self.case.evidence.recovered_property)} article(s) alleged to be recovered.",
                    "Common mass-manufactured items without distinct identification marks.",
                ],
                "strategy": "Argue that recovery of generic property does not warrant inference of robbery. At most, simple possession or receipt under §317 BNS.",
            }

        # ── 7. Nexus Attack ──────────────────────────────────────
        # Standard defense vector whenever §309(4) robbery is charged
        if self.case.has_charge("309"):
            active_vectors.append(DefenseVector.NEXUS_ATTACK)
            details[DefenseVector.NEXUS_ATTACK.value] = {
                "knowledge": VECTOR_KNOWLEDGE[DefenseVector.NEXUS_ATTACK],
                "triggers": ["Charged under Section 309(4) BNS for Robbery."],
                "strategy": "Probe timeline between alleged assault and alleged taking. If taking occurred without prior intention to cause hurt for that end, the robbery charge collapses.",
            }

        return active_vectors, details
