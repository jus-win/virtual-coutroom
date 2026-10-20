"""
defendant_agent package
────────────────────────
AI-Assisted Virtual Courtroom — Defendant Agent
Tailored for Telangana District/Sessions Courts under BNS 2023, BNSS 2023, and BSA 2023.
"""

from defendant_agent.models import (
    CaseFile,
    Accused,
    WitnessStatement,
    Evidence,
    TIPReport,
    RecoveryMahazar,
    ElectronicEvidence,
    TrialStage,
    DefenseVector,
    Speaker,
    AgentState,
    ConversationEntry,
)
from defendant_agent.database import CourtroomDatabase
from defendant_agent.strategy_analyzer import StrategyAnalyzer
from defendant_agent.prompt_builder import CourtroomPromptBuilder
from defendant_agent.file_extractor import MultiFormatFileExtractor, FileExtractionError
from defendant_agent.case_parser import CaseParser
from defendant_agent.llm_provider import (
    BaseLLMProvider,
    GeminiProvider,
    OpenAIProvider,
    OfflineMockProvider,
    get_llm_provider,
)
from defendant_agent.agent import DefendantAgent

__all__ = [
    "DefendantAgent",
    "CourtroomDatabase",
    "StrategyAnalyzer",
    "CourtroomPromptBuilder",
    "MultiFormatFileExtractor",
    "FileExtractionError",
    "CaseParser",
    "BaseLLMProvider",


    "GeminiProvider",
    "OpenAIProvider",
    "OfflineMockProvider",
    "get_llm_provider",
    "CaseFile",
    "Accused",
    "WitnessStatement",
    "Evidence",
    "TIPReport",
    "RecoveryMahazar",
    "ElectronicEvidence",
    "TrialStage",
    "DefenseVector",
    "Speaker",
    "AgentState",
    "ConversationEntry",
]
