"""
defendant_agent/case_parser.py
──────────────────────────────
Universal Case Ingestion Engine.
Accepts case details in ANY format (raw narrative, police report, FIR excerpt,
bullet points, news report, or JSON) and transforms it into a structured CaseFile
under BNS 2023, BNSS 2023, BSA 2023, and Telangana jurisdiction.
"""

from __future__ import annotations
import json
import re
from typing import Optional, Dict, Any

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
from defendant_agent.llm_provider import BaseLLMProvider, get_llm_provider


CASE_EXTRACTION_SYSTEM_PROMPT = """You are an expert Legal Data Extraction Engine specialized in Indian Criminal Law (BNS 2023, BNSS 2023, BSA 2023) and Telangana District Courts.

Your job is to read arbitrary, unformatted case details provided by the user in ANY format (raw narrative, FIR copy, police chargesheet notes, bullet points, or news summary) and extract/normalize it into a strictly valid JSON object matching the schema below.

JSON SCHEMA REQUIREMENT:
{
  "case_id": "SC/XXX/2024 (generate reasonable Sessions Case ID if omitted)",
  "court": "Court of Principal District & Sessions Judge, Rangareddy / Hyderabad / Cyberabad, Telangana",
  "judge": "Learned Sessions Judge",
  "prosecution": "Public Prosecutor for the State of Telangana",
  "hearing_date": "YYYY-MM-DD (or current/reasonable date)",
  "current_stage": "pre_trial",
  "fir_number": "FIR/Crime number from text, or '101/2024'",
  "fir_station": "Police Station name (e.g. Gachibowli PS / Madhapur PS / Banjara Hills PS)",
  "fir_date": "YYYY-MM-DD",
  "fir_time": "Time string (e.g. '22:30 hrs')",
  "fir_complainant": "Complainant name, age, occupation from text",
  "fir_content": "Detailed summary of the complainant's allegation and facts",
  "chargesheet_date": "YYYY-MM-DD",
  "chargesheet_content": "Summary of police investigation and recovery",
  "charges": [
    "BNS §309(4) (Robbery)",
    "BNS §311 (Using deadly weapon / attempt to cause death - if weapon alleged)",
    "BNS §3(5) (Joint liability - if multiple persons)"
  ],
  "accused": {
    "name": "Accused name from text (or 'Accused A-1')",
    "age": 25,
    "address": "Residential locality from text",
    "bail_status": "in_custody",
    "prior_convictions": [],
    "alibi_description": "Any alibi mentioned in text, or null if none",
    "is_first_time_offender": true
  },
  "witnesses": [
    {
      "witness_id": "PW1",
      "name": "Complainant Name",
      "witness_type": "complainant",
      "statement_s180": "Summary of what PW1 saw and reported to police"
    },
    {
      "witness_id": "PW2",
      "name": "Panch Witness Name (or local resident)",
      "witness_type": "panch",
      "statement_s180": "Witness to alleged recovery/seizure panchnama"
    },
    {
      "witness_id": "PW3",
      "name": "Investigating Officer Name",
      "witness_type": "IO",
      "statement_s180": "Investigation, arrest, and recovery steps"
    }
  ],
  "evidence": {
    "recovered_property": [
      {
        "exhibit_id": "M.O.1",
        "description": "Stolen property alleged to be seized",
        "recovery_location": "Location where recovered (e.g. open bush / roadside / house)",
        "estimated_value": 50000
      }
    ],
    "tip_report": {
      "conducted": true,
      "conducted_by": "Judicial Magistrate",
      "date": "YYYY-MM-DD",
      "identified_by": ["PW1"],
      "dummy_match": false,
      "witnesses_isolated": false,
      "prior_exposure": false,
      "delay_days": 15
    },
    "recovery_mahazar": {
      "conducted": true,
      "location": "Location from text",
      "location_type": "open",
      "panch_witnesses": ["Panch Witness Name"],
      "stock_witnesses": false,
      "property_tip_in_court": false,
      "recovery_date": "YYYY-MM-DD",
      "incident_date": "YYYY-MM-DD",
      "signed_at_police_station": false
    },
    "electronic": {
      "cctv_present": false,
      "cctv_s63_certificate": false,
      "cctv_hash_value": null,
      "cctv_description": null,
      "cdr_present": false,
      "cdr_s63_certificate": false,
      "cdr_tower_location": null
    }
  }
}

INSTRUCTIONS:
1. Extract ALL factual elements mentioned in the user's input.
2. If certain procedural details (e.g., specific court name or Section 180 statements) are not explicitly mentioned, extrapolate reasonable defaults consistent with Telangana criminal courts and BNS/BNSS 2023.
3. Classify charges under the new Bharatiya Nyaya Sanhita (BNS) 2023 (e.g. §309 for Robbery, §311 for armed robbery).
4. Return ONLY valid JSON. Do not wrap in markdown quotes if possible, or use standard ```json ... ``` code blocks.
"""


from defendant_agent.file_extractor import MultiFormatFileExtractor, FileExtractionError


class CaseParser:
    """Parses arbitrary case descriptions into CaseFile domain objects."""

    def __init__(self, llm: Optional[BaseLLMProvider] = None):
        self.llm = llm or get_llm_provider()
        self.file_extractor = MultiFormatFileExtractor(llm=self.llm)

    def parse_file(
        self,
        file_input: Any,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> CaseFile:
        """
        Ingest case materials from a file (PDF, Image, Text, or JSON),
        extract contents, and parse into a structured CaseFile.
        """
        extracted_text = self.file_extractor.extract_text(
            file_input=file_input,
            file_name=file_name,
            mime_type=mime_type,
        )
        return self.parse_raw_text(extracted_text)

    def parse_raw_text(self, raw_input: str) -> CaseFile:
        """
        Take any raw text / JSON / unformatted narrative and return a validated CaseFile.
        """
        raw_trimmed = raw_input.strip()


        # If user directly pasted JSON, try direct parsing first
        if (raw_trimmed.startswith("{") and raw_trimmed.endswith("}")) or "```json" in raw_trimmed:
            try:
                json_text = raw_trimmed
                if "```json" in json_text:
                    json_text = json_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in json_text:
                    json_text = json_text.split("```", 1)[1].split("```", 1)[0].strip()
                data = json.loads(json_text)
                if "accused" in data and ("charges" in data or "fir_content" in data):
                    return self._dict_to_casefile(data)
            except Exception:
                pass  # Fall through to LLM parser

        # Use LLM to extract structured case data from arbitrary text
        prompt = f"USER CASE DETAILS (IN ARBITRARY FORMAT):\n\n{raw_trimmed}\n\nExtract and normalize into the required JSON schema:"
        extracted_text = self.llm.generate(
            system_instruction=CASE_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=2500,
        )

        data = self._clean_and_parse_json(extracted_text, raw_trimmed)
        return self._dict_to_casefile(data)

    def _clean_and_parse_json(self, response_text: str, fallback_raw: str) -> Dict[str, Any]:
        """Strip markdown ticks and parse JSON with resilient fallback."""
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Resilient fallback if LLM response couldn't be parsed
            return self._heuristic_fallback(fallback_raw)

    def _heuristic_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Extract basic details using regex heuristics if offline/LLM fails."""
        # Find names or key patterns
        accused_match = re.search(r'(?:accused|defendant|perpetrator|suspect)[:\s]+([A-Za-z\s\.]+)', raw_text, re.IGNORECASE)
        accused_name = accused_match.group(1).strip() if accused_match else "Accused Person"

        complainant_match = re.search(r'(?:complainant|victim)[:\s]+([A-Za-z\s\.]+)', raw_text, re.IGNORECASE)
        complainant_name = complainant_match.group(1).strip() if complainant_match else "Complainant"

        return {
            "case_id": "SC/DYNAMIC/2024",
            "court": "Court of Principal District & Sessions Judge, Rangareddy, Telangana",
            "judge": "Principal District & Sessions Judge",
            "prosecution": "Public Prosecutor for Telangana",
            "hearing_date": "2024-11-20",
            "current_stage": "pre_trial",
            "fir_number": "CR/999/2024",
            "fir_station": "Cyberabad Police Station",
            "fir_date": "2024-10-01",
            "fir_time": "22:00 hrs",
            "fir_complainant": complainant_name,
            "fir_content": raw_text[:500],
            "chargesheet_date": "2024-10-25",
            "chargesheet_content": raw_text,
            "charges": [
                "BNS §309(4) (Robbery)",
                "BNS §311 (Deadly weapon robbery - 7 yr min)",
                "BNS §3(5) (Joint liability)"
            ],
            "accused": {
                "name": accused_name,
                "age": 24,
                "address": "Hyderabad, Telangana",
                "bail_status": "in_custody",
                "prior_convictions": [],
                "alibi_description": "Accused denies presence at the scene",
                "is_first_time_offender": True
            },
            "witnesses": [
                {
                    "witness_id": "PW1",
                    "name": complainant_name,
                    "witness_type": "complainant",
                    "statement_s180": raw_text[:300]
                },
                {
                    "witness_id": "PW2",
                    "name": "K. Srinivas",
                    "witness_type": "panch",
                    "statement_s180": "Panch witness to seizure of alleged stolen article from open roadside."
                },
                {
                    "witness_id": "PW3",
                    "name": "Investigating Officer",
                    "witness_type": "IO",
                    "statement_s180": "Conducted investigation, arrest, and filed chargesheet."
                }
            ],
            "evidence": {
                "recovered_property": [
                    {
                        "exhibit_id": "M.O.1",
                        "description": "Alleged stolen property",
                        "recovery_location": "Open roadside spot",
                        "estimated_value": 40000
                    }
                ],
                "tip_report": {
                  "conducted": True,
                  "conducted_by": "Judicial Magistrate",
                  "date": "2024-10-15",
                  "identified_by": ["PW1"],
                  "dummy_match": False,
                  "witnesses_isolated": False,
                  "prior_exposure": True,
                  "delay_days": 18
                },
                "recovery_mahazar": {
                  "conducted": True,
                  "location": "Open area accessible to public",
                  "location_type": "open",
                  "panch_witnesses": ["K. Srinivas"],
                  "stock_witnesses": True,
                  "property_tip_in_court": False,
                  "recovery_date": "2024-10-05",
                  "incident_date": "2024-10-01",
                  "signed_at_police_station": True
                },
                "electronic": {
                  "cctv_present": True,
                  "cctv_s63_certificate": False,
                  "cctv_hash_value": None,
                  "cctv_description": "CCTV footage without §63 certificate",
                  "cdr_present": False,
                  "cdr_s63_certificate": False,
                  "cdr_tower_location": None
                }
            }
        }

    def _dict_to_casefile(self, data: Dict[str, Any]) -> CaseFile:
        """Convert standard extracted dict into CaseFile domain object."""
        acc_data = data.get("accused", {})
        accused = Accused(
            name=acc_data.get("name", "Accused Person"),
            age=acc_data.get("age", 25),
            address=acc_data.get("address", ""),
            bail_status=acc_data.get("bail_status", "in_custody"),
            prior_convictions=acc_data.get("prior_convictions", []),
            alibi_description=acc_data.get("alibi_description"),
            is_first_time_offender=acc_data.get("is_first_time_offender", True),
        )

        witnesses = [
            WitnessStatement(
                witness_id=w.get("witness_id", f"PW{idx+1}"),
                name=w.get("name", f"Witness {idx+1}"),
                witness_type=w.get("witness_type", "complainant"),
                statement_s180=w.get("statement_s180", ""),
            )
            for idx, w in enumerate(data.get("witnesses", []))
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
            case_id=data.get("case_id", "SC/DYNAMIC/2024"),
            court=data.get("court", "Court of Principal District & Sessions Judge, Rangareddy, Telangana"),
            judge=data.get("judge", "Principal District & Sessions Judge"),
            prosecution=data.get("prosecution", "Public Prosecutor for Telangana"),
            hearing_date=data.get("hearing_date", "2024-11-20"),
            current_stage=TrialStage.from_str(data.get("current_stage", "pre_trial")),
            fir_number=data.get("fir_number", "CR/999/2024"),
            fir_station=data.get("fir_station", "Cyberabad PS"),
            fir_date=data.get("fir_date", "2024-10-01"),
            fir_time=data.get("fir_time", "22:00 hrs"),
            fir_complainant=data.get("fir_complainant", "Complainant"),
            fir_content=data.get("fir_content", ""),
            chargesheet_date=data.get("chargesheet_date", "2024-10-25"),
            chargesheet_content=data.get("chargesheet_content", ""),
            charges=data.get("charges", ["BNS §309(4) (Robbery)"]),
            accused=accused,
            witnesses=witnesses,
            evidence=evidence,
        )
