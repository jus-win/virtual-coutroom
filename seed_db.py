"""
seed_db.py
──────────
Utility script to load sample case JSON files into the SQLite database.
Usage:
    python seed_db.py [path_to_case_json]
"""

from __future__ import annotations
import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from defendant_agent.models import (
    CaseFile,
    Accused,
    WitnessStatement,
    Evidence,
    TIPReport,
    RecoveryMahazar,
    ElectronicEvidence,
    TrialStage,
)
from defendant_agent.database import CourtroomDatabase
from defendant_agent.strategy_analyzer import StrategyAnalyzer


def load_case_from_json(json_path: Path) -> CaseFile:
    """Parse a structured case JSON file into a CaseFile domain object."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    accused_data = data["accused"]
    accused = Accused(
        name=accused_data["name"],
        age=accused_data["age"],
        address=accused_data.get("address", ""),
        bail_status=accused_data.get("bail_status", "in_custody"),
        prior_convictions=accused_data.get("prior_convictions", []),
        alibi_description=accused_data.get("alibi_description"),
        is_first_time_offender=accused_data.get("is_first_time_offender", True),
    )

    witnesses = [
        WitnessStatement(
            witness_id=w["witness_id"],
            name=w["name"],
            witness_type=w["witness_type"],
            statement_s180=w["statement_s180"],
        )
        for w in data.get("witnesses", [])
    ]

    evi_data = data.get("evidence", {})
    tip_data = evi_data.get("tip_report")
    tip_report = (
        TIPReport(
            conducted=tip_data.get("conducted", False),
            conducted_by=tip_data.get("conducted_by"),
            date=tip_data.get("date"),
            identified_by=tip_data.get("identified_by", []),
            dummy_match=tip_data.get("dummy_match", True),
            witnesses_isolated=tip_data.get("witnesses_isolated", True),
            prior_exposure=tip_data.get("prior_exposure", False),
            delay_days=tip_data.get("delay_days", 0),
        )
        if tip_data
        else None
    )

    mahazar_data = evi_data.get("recovery_mahazar")
    recovery_mahazar = (
        RecoveryMahazar(
            conducted=mahazar_data.get("conducted", False),
            location=mahazar_data.get("location"),
            location_type=mahazar_data.get("location_type", "open"),
            panch_witnesses=mahazar_data.get("panch_witnesses", []),
            stock_witnesses=mahazar_data.get("stock_witnesses", False),
            property_tip_in_court=mahazar_data.get("property_tip_in_court", False),
            recovery_date=mahazar_data.get("recovery_date"),
            incident_date=mahazar_data.get("incident_date"),
            signed_at_police_station=mahazar_data.get("signed_at_police_station", False),
        )
        if mahazar_data
        else None
    )

    elec_data = evi_data.get("electronic")
    electronic = (
        ElectronicEvidence(
            cctv_present=elec_data.get("cctv_present", False),
            cctv_s63_certificate=elec_data.get("cctv_s63_certificate", False),
            cctv_hash_value=elec_data.get("cctv_hash_value"),
            cctv_description=elec_data.get("cctv_description"),
            cdr_present=elec_data.get("cdr_present", False),
            cdr_s63_certificate=elec_data.get("cdr_s63_certificate", False),
            cdr_tower_location=elec_data.get("cdr_tower_location"),
        )
        if elec_data
        else None
    )

    evidence = Evidence(
        recovered_property=evi_data.get("recovered_property", []),
        tip_report=tip_report,
        fsl_report=evi_data.get("fsl_report"),
        electronic=electronic,
        recovery_mahazar=recovery_mahazar,
    )

    return CaseFile(
        case_id=data["case_id"],
        court=data["court"],
        judge=data.get("judge"),
        prosecution=data.get("prosecution"),
        hearing_date=data.get("hearing_date"),
        current_stage=TrialStage.from_str(data.get("current_stage", "pre_trial")),
        fir_number=data["fir_number"],
        fir_station=data["fir_station"],
        fir_date=data["fir_date"],
        fir_time=data["fir_time"],
        fir_complainant=data["fir_complainant"],
        fir_content=data["fir_content"],
        chargesheet_date=data["chargesheet_date"],
        chargesheet_content=data["chargesheet_content"],
        charges=data.get("charges", []),
        accused=accused,
        witnesses=witnesses,
        evidence=evidence,
    )


def seed(json_file_path: Optional[str] = None, db_path: str = "courtroom.db") -> CaseFile:
    """Load JSON file and seed into SQLite."""
    default_json = Path(__file__).parent / "sample_cases" / "robbery_case_001.json"
    target_path = Path(json_file_path) if json_file_path else default_json

    if not target_path.exists():
        raise FileNotFoundError(f"Case file not found: {target_path}")

    print(f"[*] Reading case file: {target_path}")
    case = load_case_from_json(target_path)

    print(f"[*] Connecting to SQLite database: {db_path}")
    db = CourtroomDatabase(db_path=db_path)
    db.save_case(case)
    print(f"[+] Case successfully saved to database: {case.case_id}")

    # Perform strategy analysis check
    analyzer = StrategyAnalyzer(case)
    vectors, details = analyzer.analyze()
    print("\n" + "=" * 65)
    print(f"CASE LOADED: {case.case_id}")
    print(f"Court:       {case.court}")
    print(f"Accused:     {case.accused.name} (Age: {case.accused.age})")
    print(f"Charges:     {', '.join(case.charges)}")
    print(f"Witnesses:   {len(case.witnesses)} ({', '.join(w.witness_id for w in case.witnesses)})")
    print("-" * 65)
    print("DETECTED DEFENSE VECTORS:")
    for v in vectors:
        print(f"  * {v.value.upper()}: {v.description()}")
    print("=" * 65 + "\n")

    return case


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    seed(path_arg)
