# AI-Assisted Virtual Courtroom — Defendant Agent
### District Court / Sessions Court Level (Robbery Cases — State of Telangana)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![SQLite](https://img.shields.io/badge/database-SQLite-lightgrey.svg)](https://sqlite.org/)
[![Legal Corpus](https://img.shields.io/badge/jurisprudence-BNS%20|%20BNSS%20|%20BSA%202023-gold.svg)]()
[![Status](https://img.shields.io/badge/status-ready%20for%20orchestrator%20integration-brightgreen.svg)]()

A modular, plug-and-play **Defendant AI Agent** designed for law student educational simulations. The agent simulates a senior criminal defense advocate appearing before the Principal District and Sessions Court in Telangana, India for criminal robbery cases under the new criminal codes (**BNS 2023**, **BNSS 2023**, and **BSA 2023**).

---

## 🏛️ System Architecture

The agent is designed to plug directly into a multi-agent courtroom orchestrator coordinating three primary agents:
1. **Judge Agent**: Presides over hearings, issues stage rulings, passes orders on bail, discharge, and final verdict.
2. **Prosecutor Agent** (or Law Student): Files charges, examines prosecution witnesses, opposes bail/discharge, argues for conviction.
3. **Defendant Agent** (*This package*): Defends the accused, identifies procedural lapses, conducts surgical cross-examinations, rebuts presumptions, and moves for bail/discharge/acquittal.

```
┌────────────────────────────────────────────────────────┐
│        Virtual Courtroom Multi-Agent Orchestrator      │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
       ┌────────▼───────┐       ┌────────▼───────┐
       │   Judge Agent  │       │Prosecutor Agent│
       └────────────────┘       │ (or Student)   │
                                └────────────────┘
                │
       ┌────────▼────────────────────────────────────────┐
       │             Defendant AI Agent                  │
       │                                                 │
       │  ┌─────────────────┐    ┌────────────────────┐  │
       │  │Strategy Analyzer│    │   Prompt Builder   │  │
       │  │ (8 Law Vectors) │    │  (9 Trial Stages)  │  │
       │  └────────┬────────┘    └─────────┬──────────┘  │
       │           │                       │             │
       │  ┌────────▼───────────────────────▼──────────┐  │
       │  │         LLM Provider Adapter              │  │
       │  │  (Google Gemini / OpenAI / Offline Mock)   │  │
       │  └────────────────────┬──────────────────────┘  │
       └───────────────────────┼─────────────────────────┘
                               │
                      ┌────────▼────────┐
                      │ SQLite Database │
                      │ (courtroom.db)  │
                      └─────────────────┘
```

---

## ⚖️ Legal Grounding & Jurisprudence

| Legislative Pillar | Relevant Sections / Rules | Practical Defense Application |
|---|---|---|
| **Bharatiya Nyaya Sanhita (BNS) 2023** | §309(4) (Robbery)<br>§311 (Deadly weapon)<br>§304 (Snatching)<br>§317 (Stolen goods) | **Nexus Attack**: Force was not used *for that end* (*Joseph Mingel Koli*).<br>**Individual Liability**: §311 is personal, not vicarious (*Phool Kumar*). |
| **Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023** | §230 (Document supply)<br>§232 (Committal)<br>§250 (Discharge)<br>§254 (Witness exam)<br>§257 (Arguments)<br>§479/§480 (Bail) | **Statutory Timelines & Bail Rights**: First-time offender 1/3 custody bail rule under §479(1); discharge when allegations disclose no grave suspicion (*Sanjay Kumar Rai*). |
| **Bharatiya Sakshya Adhiniyam (BSA) 2023** | §7 (Identity)<br>§9 (Alibi)<br>§23 proviso (Discovery)<br>§63(4) (Digital cert)<br>§104 (Burden of proof)<br>§119 (Presumption) | **Evidentiary Attacks**: Open place recovery without exclusive possession (*Bodhraj*); mandatory §63(4) certificate & hash for CCTV/CDR (*Arjun Panditrao Khotkar*). |
| **Telangana Criminal Rules of Practice, 1990** | Rule 34 (TIP Procedure)<br>Rule 35 (Property ID) | **Vitiation of Identification**: Inordinate delay (>14 days), non-isolation of witnesses, prior photo exposure, and holding property parade outside Magistrate's court. |

---

## 📂 Project Structure

```
virtual-courtroom/
├── schema.sql                           # SQLite database schema
├── requirements.txt                     # Dependencies
├── .env.example                         # Environment variables configuration
├── seed_db.py                           # Database seeder from JSON case files
├── main.py                              # CLI simulation runner & demo
├── sample_cases/
│   └── robbery_case_001.json            # Realistic Telangana Sessions robbery case
├── defendant_agent/
│   ├── __init__.py                      # Public package exports
│   ├── models.py                        # Dataclasses & Enums (TrialStage, DefenseVector)
│   ├── database.py                      # SQLite persistence layer
│   ├── strategy_analyzer.py             # 8-vector legal defense analysis engine
│   ├── prompt_builder.py                # 9-stage prompt builder with Telangana decorum
│   ├── llm_provider.py                  # Gemini, OpenAI & Offline Mock fallback
│   └── agent.py                         # Core DefendantAgent integration class
└── tests/
    └── test_defendant_agent.py          # Automated test suite (100% pass)
```

---

## 🔌 Multi-Agent Framework Integration Interface

The `DefendantAgent` class provides a simple API for your orchestrator:

```python
from defendant_agent import DefendantAgent, CourtroomDatabase, TrialStage, Speaker

# 1. Connect to SQLite and initialize agent for a specific case
db = CourtroomDatabase("courtroom.db")
defendant = DefendantAgent(case_id="SC/142/2024", db=db)

# 2. Advance trial stage (called by Judge / Orchestrator)
defendant.advance_stage(TrialStage.BAIL_HEARING)

# 3. Take a turn in response to Judge, Prosecutor, or Student
response = defendant.take_turn(
    incoming_message="Public Prosecutor opposes regular bail under Section 311 BNS.",
    incoming_speaker=Speaker.PROSECUTOR,
)
print("Defense Submission:", response)

# 4. Cross-examination targeting
defendant.advance_stage(TrialStage.PROSECUTION_EVIDENCE)
defendant.set_cross_examination_witness("PW1")
cross_exam_questions = defendant.take_turn(
    incoming_message="PW1 Rajesh Sharma is tendered for cross-examination.",
    incoming_speaker=Speaker.PROSECUTOR,
)

# 5. Get agent status for dashboard / state coordinator
status = defendant.get_status()
# Returns: case_id, current_stage, active_strategies, current_witness, etc.

# 6. Generate Pre-Trial Strategy Brief
brief = defendant.generate_defense_brief()
# Returns: active vectors, statutory authorities, and prosecution vulnerabilities
```

---

## 🚀 Quickstart Guide

### 1. Installation
```powershell
cd C:\Users\JASWIN\.gemini\antigravity\scratch\virtual-courtroom
pip install -r requirements.txt
```

### 2. Configure API Key (Optional)
Copy `.env.example` to `.env` and configure your API key:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-1.5-pro
```
> **Note**: If no API key is configured, the system automatically uses the built-in **`OfflineMockProvider`**, enabling complete offline testing, demonstrations, and test execution without API costs!

### 3. Run Automated 5-Stage Courtroom Simulation
Demonstrates the agent sequentially defending through Bail Hearing, Discharge Application, PW1 Cross-Exam, PW2 Cross-Exam, and Final Arguments:
```powershell
python main.py
```

### 4. Interactive Simulation Mode
Step into the shoes of the Judge, Prosecutor, or Law Student and dialogue directly with the Defense Counsel:
```powershell
python main.py --interactive
```
Interactive commands available:
- `/stage <stage_name>`: Switch stage (`bail_hearing`, `discharge_application`, `charge_framing`, `prosecution_evidence`, `final_arguments`)
- `/as <role>`: Switch persona (`JUDGE`, `PROSECUTOR`, `STUDENT_PROSECUTOR`)
- `/witness <pw_id>`: Set witness in witness box (`PW1`, `PW2`)
- `/brief`: View full defense strategy report
- `/status`: Show trial state

### 5. View Pre-Trial Defense Brief
```powershell
python main.py --brief
```

### 6. Run the Test Suite
```powershell
python -m unittest tests/test_defendant_agent.py
```

---

## 🗄️ SQLite Database Schema Summary

- `cases`: Immutable case file records, FIR details, chargesheet, and charges.
- `accused`: Accused demographics, alibi claims, bail status, and prior history.
- `witnesses`: Prosecution witnesses (PW1–PW4) and their §180 BNSS police statements.
- `evidence_items`: Property seizures, TIP reports, FSL records, and electronic evidence (§63 BSA).
- `conversations`: Chronological log of all utterances across all courtroom speakers.
- `trial_state`: Live simulation stage, active strategy vectors, and cross-examination targets.
