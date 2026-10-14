"""
main.py
───────
Interactive CLI & Demonstration Runner for the Defendant AI Agent.
Simulates District Court / Sessions Court proceedings in Telangana.

Usage:
    python main.py                  # Runs automated 5-stage courtroom simulation
    python main.py --interactive    # Interactive chat mode (You act as Judge / Prosecutor)
    python main.py --brief          # Prints comprehensive Pre-Trial Defense Brief
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

# Reconfigure stdout for utf-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from defendant_agent.models import TrialStage, Speaker
from defendant_agent.database import CourtroomDatabase
from defendant_agent.agent import DefendantAgent
from defendant_agent.llm_provider import get_llm_provider
from seed_db import seed


def print_banner() -> None:
    print("\n" + "=" * 70)
    print("   AI-ASSISTED VIRTUAL COURTROOM -- DEFENDANT AGENT")
    print("   Sessions Court / District Court Level (Telangana Jurisdiction)")
    print("   Laws: BNS 2023 | BNSS 2023 | BSA 2023 | Telangana CRoP 1990")
    print("=" * 70 + "\n")



def print_defense_brief(agent: DefendantAgent) -> None:
    """Display structured defense strategy brief."""
    brief = agent.generate_defense_brief()
    print_banner()
    print(f"[*] PRE-TRIAL DEFENSE STRATEGY BRIEF -- Case: {brief['case_id']}")
    print("-" * 70)
    accused = brief["accused"]
    print(f"Accused:              {accused['name']} (Age: {accused['age']})")
    print(f"Bail Status:          {accused['bail_status'].upper()}")
    print(f"First-Time Offender:  {accused['first_time_offender']}")
    print(f"Alibi:                {accused['alibi']}")
    print(f"Charges:              {', '.join(brief['charges'])}")
    print("-" * 70)

    print("\n[ACTIVE DEFENSE STRATEGY VECTORS]")
    for v in brief["active_vectors"]:
        print(f"\n* [{v['vector'].upper()}] - {v['description']}")
        details = v.get("details", {})
        if "knowledge" in details:
            k = details["knowledge"]
            print(f"  - Statute:   {k['statute']}")
            print(f"  - Case Law:  {k['precedent']}")
            print(f"  - Strategy:  {details.get('strategy', '')}")
        elif "triggers" in details:
            print(f"  - Triggers:  {', '.join(details['triggers'])}")

    print("\n[PROSECUTION VULNERABILITIES IDENTIFIED]")
    print("1. Test Identification Parade (CRoP Rule 34):")
    for tip_vuln in brief["tip_vulnerabilities"]:
        print(f"   - {tip_vuln}")

    print("2. Recovery Mahazar (Section 23 BSA Proviso):")
    for rec_vuln in brief["recovery_vulnerabilities"]:
        print(f"   - {rec_vuln}")

    print("3. Electronic Evidence (Section 63 BSA 2023):")
    for el_vuln in brief["electronic_vulnerabilities"]:
        print(f"   - {el_vuln}")
    print("=" * 70 + "\n")


def run_automated_simulation(agent: DefendantAgent) -> None:
    """
    Demonstrates the Defendant Agent taking turns across multiple stages
    of a criminal trial in the Sessions Court.
    """
    print_banner()
    print("[*] Starting multi-stage simulated trial session...\n")

    stages_and_prompts = [
        (
            TrialStage.BAIL_HEARING,
            Speaker.JUDGE,
            "The court calls Sessions Case No. 142 of 2024. Accused Mohd. Farhan is produced from judicial custody. "
            "Public Prosecutor opposes bail stating Section 311 BNS carries a 7-year minimum punishment and recovery was made. "
            "Defense Counsel, what is your submission on regular bail?",
        ),
        (
            TrialStage.DISCHARGE_APPLICATION,
            Speaker.JUDGE,
            "We have perused the chargesheet and Section 230 BNSS documents. Learned Public Prosecutor prays for framing "
            "charges under Section 309(4) and Section 311 BNS. Does the Defense Counsel move for discharge under Section 250 BNSS?",
        ),
        (
            TrialStage.PROSECUTION_EVIDENCE,
            Speaker.PROSECUTOR,
            "PW-1 (Complainant Rajesh Sharma) is in the witness box. PW-1 has deposed that he was robbed at 23:30 hrs near "
            "Wipro Circle and identified Accused Mohd. Farhan in Cherlapally prison. The witness is now tendered for cross-examination.",
        ),
        (
            TrialStage.PROSECUTION_EVIDENCE,
            Speaker.PROSECUTOR,
            "PW-2 (Panch Witness K. Venkat Rao) has testified that Accused led police to the bushes on Botanical Garden road "
            "and recovered the complainant's OnePlus mobile phone under Ex.P-2. Witness is tendered for cross-examination.",
        ),
        (
            TrialStage.FINAL_ARGUMENTS,
            Speaker.JUDGE,
            "Prosecution evidence is closed. Section 351 BNSS examination is completed. The Court now calls upon the Defense Counsel "
            "to advance final arguments under Section 257 BNSS.",
        ),
    ]

    for stage, speaker, trigger_msg in stages_and_prompts:
        agent.advance_stage(stage)
        print(f"\n{'-' * 70}")
        print(f">> TRIAL STAGE: {stage.label().upper()}")
        print(f"{'-' * 70}")
        print(f"[{speaker.value}]:\n\"{trigger_msg}\"\n")

        print("[DEFENSE COUNSEL RESPONDING...]")
        defense_reply = agent.take_turn(
            incoming_message=trigger_msg,
            incoming_speaker=speaker,
        )
        print(f"\n[DEFENSE COUNSEL (ADV. FOR ACCUSED)]:\n{defense_reply}\n")



def run_interactive_mode(agent: DefendantAgent) -> None:
    """Interactive loop where the user types as Judge or Prosecutor."""
    print_banner()
    print("Welcome to Interactive Courtroom Mode!")
    print("You can simulate the role of the Judge, Prosecutor, or Law Student.")
    print("Commands:")
    print("  /stage <stage_name>   - Change stage (bail_hearing, discharge, charge_framing, evidence, final_arguments)")
    print("  /witness <pw_id>      - Set current witness (e.g. PW1, PW2)")
    print("  /status               - Show current trial status")
    print("  /brief                - View Defense Strategy Brief")
    print("  /exit or /quit        - Exit simulation\n")

    speaker = Speaker.JUDGE

    while True:
        try:
            user_input = input(f"\n[{speaker.value}] Enter message (or command) > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                print("\nAdjourning court. Goodbye!")
                break

            if user_input.startswith("/stage "):
                new_stage_str = user_input.split(" ", 1)[1].strip()
                agent.advance_stage(new_stage_str)
                print(f"[+] Trial stage updated to: {agent.state.current_stage.label()}")
                continue

            if user_input.startswith("/witness "):
                pw = user_input.split(" ", 1)[1].strip().upper()
                agent.set_cross_examination_witness(pw)
                print(f"[+] Witness box set to: {pw}")
                continue

            if user_input.lower() == "/status":
                status = agent.get_status()
                print("\n--- CURRENT TRIAL STATUS ---")
                for k, v in status.items():
                    print(f"  {k}: {v}")
                continue

            if user_input.lower() == "/brief":
                print_defense_brief(agent)
                continue

            if user_input.lower().startswith("/as "):
                role = user_input.split(" ", 1)[1].strip().upper()
                if role in ("JUDGE", "PROSECUTOR", "STUDENT_PROSECUTOR", "STUDENT_DEFENSE"):
                    speaker = Speaker(role)
                    print(f"[+] Your speaker role is now: {speaker.value}")
                else:
                    print(f"[-] Unknown role '{role}'. Use JUDGE, PROSECUTOR, or STUDENT_PROSECUTOR.")
                continue

            # Generate defense counsel response
            print("\n⚖️  [DEFENSE COUNSEL RESPONDING...]")
            response = agent.take_turn(
                incoming_message=user_input,
                incoming_speaker=speaker,
            )
            print(f"\n[DEFENSE COUNSEL]:\n{response}")

        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break


def main():
    parser = argparse.ArgumentParser(description="AI-Assisted Virtual Courtroom — Defendant Agent")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive CLI chat session")
    parser.add_argument("--brief", action="store_true", help="Print pre-trial defense strategy brief")
    parser.add_argument("--case", default=None, help="Path to custom case JSON file")
    parser.add_argument("--db", default="courtroom.db", help="Path to SQLite database")
    args = parser.parse_args()

    # Ensure database is seeded
    case = seed(args.case, db_path=args.db)

    # Instantiate the agent
    db = CourtroomDatabase(db_path=args.db)
    agent = DefendantAgent(case_id=case.case_id, db=db)

    if args.brief:
        print_defense_brief(agent)
    elif args.interactive:
        run_interactive_mode(agent)
    else:
        run_automated_simulation(agent)


if __name__ == "__main__":
    main()
