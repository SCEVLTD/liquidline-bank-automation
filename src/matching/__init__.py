"""
Matching Engine Package

4-Layer Matching System:
- Layer 1: Exact SI-XXXXXX invoice pattern matching
- Layer 2: AKA sheet pattern lookup
- Layer 3: Fuzzy customer name matching
- Layer 4: Claude AI inference for ambiguous cases
"""

from .layer1_si import SIInvoiceMatcher
from .layer2_aka import AKAMatcher
from .layer3_fuzzy import FuzzyMatcher
from .layer4_ai import AIMatcher
from .orchestrator import MatchingOrchestrator

__all__ = [
    "SIInvoiceMatcher",
    "AKAMatcher",
    "FuzzyMatcher",
    "AIMatcher",
    "MatchingOrchestrator"
]
