"""
defendant_agent/llm_provider.py
───────────────────────────────
Unified LLM Provider supporting Google Gemini, OpenAI, and a Mock/Offline fallback.
Allows seamless plug-and-play switching without modifying agent logic.
"""

from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseLLMProvider(ABC):
    """Abstract interface for LLM calls in the courtroom simulation."""

    @abstractmethod
    def generate(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        """Generate response text given system instructions and user prompt."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider using google-generativeai."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set the environment variable or pass api_key."
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. Run: pip install google-generativeai"
            )

    def generate(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        generation_config = self._genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        model = self._genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )
        response = model.generate_content(user_prompt)
        return response.text.strip()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider using openai python sdk."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o")

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set the environment variable or pass api_key."
            )

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def generate(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()


class OfflineMockProvider(BaseLLMProvider):
    """
    Deterministic offline fallback provider for testing and demonstration
    when API keys are not supplied. Produces authentic legal defense responses.
    """

    def generate(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        # Extract the latest input section if available
        if "LATEST INPUT:" in user_prompt:
            target_text = user_prompt.split("LATEST INPUT:", 1)[1].lower()
        else:
            target_text = user_prompt.lower()

        sys_lower = system_instruction.lower()

        if "pw-2" in target_text or "pw2" in target_text or "panch" in target_text or "ex.p-2" in target_text:
            return (
                "With the leave of the Hon'ble Court, Cross-Examination of PW-2 (Panch Witness K. Venkat Rao):\n\n"
                "Q1. Isn't it true that the Botanical Garden road is a heavily trafficked public road accessible to every member of the public day and night?\n"
                "Q2. You have admitted that the bush where the mobile phone was allegedly found was completely unfenced and open to the road, haven't you?\n"
                "Q3. How many times before this case have you acted as a panch witness for the Gachibowli Police Station? Isn't it a fact that you are a stock panch for this police station?\n"
                "Q4. Did you sign the panchnama at the scene of alleged recovery, or were your signatures obtained on blank typed papers at the police station?\n\n"
                "Submission: The defense submits that under the law laid down by the Hon'ble Supreme Court in *Bodhraj v. State of J&K (2002)*, "
                "a recovery from an open space accessible to all cannot be attributed to the exclusive conscious possession of the accused under Section 23 BSA proviso."
            )
        elif "pw-1" in target_text or "pw1" in target_text or "complainant" in target_text or "wipro circle" in target_text:
            return (
                "With the permission of the Hon'ble Court, Cross-Examination of PW-1 (Complainant Rajesh Sharma):\n\n"
                "Q1. In your statement under Section 180 BNSS, you stated that the incident took place in the dark under flickering streetlights at 23:30 hrs, correct?\n"
                "Q2. You also admitted that the motorcycle rider was wearing a full-face helmet with a tinted visor throughout the encounter, did you not?\n"
                "Q3. Isn't it a fact that before the learned Magistrate conducted the TIP on 08-09-2024 -- after an unexplained delay of 19 days -- the Gachibowli police showed you photographs of this accused?\n"
                "Q4. I put it to you that you identified this accused in court not because you recognized him from the crime scene, but because his photographs were circulated to you prior to the parade.\n\n"
                "Submission: The dock identification is wholly vitiated and unsafe under Rule 34 of the Telangana Criminal Rules of Practice and *Shaikh Umar Ahmed Shaikh v. State of Maharashtra*."
            )
        elif "discharge" in target_text or "250" in target_text or "discharge_application" in sys_lower:
            return (
                "May it please your Honour. The defense moves an application for discharge under Section 250 of the "
                "Bharatiya Nagarik Suraksha Sanhita, 2023.\n\n"
                "A bare perusal of the chargesheet and materials submitted under Section 230 BNSS demonstrates that even if the "
                "entire prosecution narrative is accepted on its face value, no prima facie case for robbery under Section 309(4) "
                "of BNS is disclosed against this accused.\n\n"
                "1. **No Deadly Weapon under §311 BNS**: The complainant's own statement attributes the iron rod solely to the absconding pillion rider. "
                "As held in *Phool Kumar v. Delhi Administration (1975)*, Section 311 BNS does not permit vicarious liability.\n"
                "2. **Force not for the purpose of theft**: There is no nexus between the alleged assault and the taking of property (*Joseph Mingel Koli*).\n"
                "3. **Inadmissible Digital Evidence**: The CCTV footage lacks the mandatory Section 63(4) BSA certificate and SHA-256 hash (*Arjun Panditrao Khotkar*).\n\n"
                "In *Sanjay Kumar Rai v. State of Uttar Pradesh (2021)*, the Supreme Court held that the court must evaluate if allegations disclose grave suspicion. "
                "We pray that the accused be discharged."
            )
        elif "final" in target_text or "257" in target_text or "final_arguments" in sys_lower:
            return (
                "May it please the Hon'ble Sessions Court. Final arguments on behalf of Accused Mohd. Farhan under Section 257 BNSS, 2023:\n\n"
                "1. **Fatal Infirmity in Identification**: The sole eyewitness PW1 had poor visibility. The TIP was conducted after an inordinate delay of 19 days, "
                "with non-matching dummies and prior photo exposure, violating Rule 34 of the Telangana Criminal Rules of Practice, 1990 (*Shaikh Umar Ahmed Shaikh*).\n"
                "2. **Recovery from Open Place Inadmissible**: The alleged recovery of M.O.1 from an open public roadside bush does not establish exclusive conscious "
                "possession under Section 23 BSA proviso (*Bodhraj v. State of J&K*). PW2 is a stock panch witness.\n"
                "3. **Unassailable Defense Alibi**: The digital delivery records prove the accused was 3.5 km away at Financial District at 23:25 hrs. IO deliberately failed "
                "to verify the defense plea under Section 9 BSA.\n"
                "4. **No Section 311 BNS Liability**: No weapon was ever recovered from or used by this accused (*Phool Kumar*).\n\n"
                "The prosecution has miserably failed to prove guilt beyond reasonable doubt. The accused is entitled to an honorable acquittal under Section 258 BNSS."
            )
        elif "bail" in target_text or "480" in target_text or "479" in target_text or "bail_hearing" in sys_lower:
            return (
                "May it please this Hon'ble Court. On behalf of applicant/accused Mohd. Farhan, we move this application "
                "under Section 480 read with Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023.\n\n"
                "1. The applicant is a 22-year-old youth with no prior criminal antecedents, entitled to mandatory consideration as a first-time offender under Section 479(1) BNSS.\n"
                "2. Investigation is complete, chargesheet has been filed, and custodial interrogation is no longer required.\n"
                "3. Section 311 BNS is improperly invoked against him as he carried no weapon (*Phool Kumar*).\n"
                "4. As settled in *Satender Kumar Antil v. CBI (2022)*, bail is the rule and jail is the exception.\n\n"
                "The applicant has deep family roots in Cyberabad and undertakes to abide by all stringent conditions imposed by this Hon'ble Court. We pray for regular bail."
            )
        else:
            return (
                "May it please the Hon'ble Court. The defense submits that the burden of proving every constituent element of the "
                "offence rests squarely upon the prosecution under Section 104 of the Bharatiya Sakshya Adhiniyam, 2023.\n\n"
                "We respectfully contest the submissions advanced by the learned Public Prosecutor. The record reveals serious lacunae "
                "in procedural adherence under the BNSS 2023 and the Telangana Criminal Rules of Practice. The defense prays that the "
                "lawful rights of the accused be safeguarded at this stage of the proceedings."
            )



def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Factory function to instantiate the chosen LLM provider.
    Defaults to Gemini if GEMINI_API_KEY is present, then OpenAI, then OfflineMockProvider.
    """
    p_name = (provider_name or os.getenv("LLM_PROVIDER", "")).lower()

    if p_name == "gemini" or (not p_name and os.getenv("GEMINI_API_KEY")):
        try:
            return GeminiProvider(api_key=api_key, model_name=model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-pro"))
        except Exception as e:
            print(f"[Warning] Failed to initialize Gemini ({e}). Falling back to OfflineMockProvider.")
            return OfflineMockProvider()

    elif p_name == "openai" or (not p_name and os.getenv("OPENAI_API_KEY")):
        try:
            return OpenAIProvider(api_key=api_key, model_name=model_name or os.getenv("OPENAI_MODEL", "gpt-4o"))
        except Exception as e:
            print(f"[Warning] Failed to initialize OpenAI ({e}). Falling back to OfflineMockProvider.")
            return OfflineMockProvider()

    else:
        # Default fallback for testing and development
        return OfflineMockProvider()
