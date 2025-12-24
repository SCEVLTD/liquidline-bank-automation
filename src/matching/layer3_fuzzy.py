"""
Liquidline Bank Reconciliation Automation
Layer 3: Fuzzy Customer Name Matcher

Uses fuzzy string matching to identify customers
when exact patterns don't match.

Coverage: ~30% of transactions
Accuracy: ~85%
"""

from typing import List, Optional, Tuple
import logging
import re

from rapidfuzz import fuzz, process

from ..models.transaction import (
    Transaction, MatchResult, ConfidenceLevel, MatchMethod
)
from ..data.customer_loader import CustomerLoader

logger = logging.getLogger(__name__)


def normalize_company_name(name: str) -> str:
    """
    Normalize company name by removing common suffixes.

    This dramatically improves fuzzy matching accuracy by removing
    suffixes like LTD, Limited, PLC that cause false matches.

    Example:
        'FREIGHTLINER LTD' -> 'FREIGHTLINER'
        'CVS (UK) Limited' -> 'CVS'
    """
    if not name:
        return ''

    name = name.upper().strip()

    # Remove common company suffixes (order matters - longer patterns first)
    suffixes = [
        r'\s*\(UK\)\s*LIMITED$',
        r'\s*\(UK\)\s*LTD$',
        r'\s*\(UK\)$',
        r'\s+UK\s+LIMITED$',
        r'\s+UK\s+LTD$',
        r'\s+LIMITED$',
        r'\s+LTD\.?$',
        r'\s+PLC$',
        r'\s+LLC$',
        r'\s+INC\.?$',
        r'\s+CORP\.?$',
        r'\s+GROUP$',
        r'\s+HOLDINGS$',
        r'\s+SERVICES$',
        r'\s+COMPANY$',
        r'\s+CO\.?$',
    ]

    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)

    # Remove trailing punctuation and whitespace
    name = re.sub(r'[\s\.,]+$', '', name)

    return name.strip()


class FuzzyMatcher:
    """
    Layer 3 Matcher: Fuzzy Customer Name Matching

    Uses rapidfuzz library for efficient fuzzy string matching
    against the customer master database.

    Key improvements:
    - Normalizes company names (removes LTD, Limited, PLC, etc.)
    - Uses fuzz.ratio on normalized names for accurate matching
    - Uses fuzz.partial_ratio as fallback for truncated bank names
    """

    # Minimum score thresholds (on normalized names)
    HIGH_CONFIDENCE_THRESHOLD = 90
    MEDIUM_CONFIDENCE_THRESHOLD = 75
    MIN_MATCH_THRESHOLD = 65

    def __init__(self, customer_loader: Optional[CustomerLoader] = None):
        """
        Args:
            customer_loader: Loaded customer data, or None to load later
        """
        self.customer_loader = customer_loader
        self._customer_names_cache: List[str] = []  # Original names
        self._normalized_names_cache: List[str] = []  # Normalized names
        self._name_to_code: dict = {}  # Original name -> code
        self._normalized_to_original: dict = {}  # Normalized -> original name

    def set_loader(self, customer_loader: CustomerLoader):
        """Set the customer loader and build name cache"""
        self.customer_loader = customer_loader
        self._build_cache()

    def _build_cache(self):
        """Build the customer name cache for fuzzy matching"""
        if not self.customer_loader:
            return

        self._customer_names_cache = []
        self._normalized_names_cache = []
        self._name_to_code = {}
        self._normalized_to_original = {}

        for code, customer in self.customer_loader.customers.items():
            name = customer.get('name', '').strip()
            if name and name.lower() != 'nan':
                # Store original name
                self._customer_names_cache.append(name)
                self._name_to_code[name.upper()] = code

                # Store normalized name for better matching
                normalized = normalize_company_name(name)
                if normalized:
                    self._normalized_names_cache.append(normalized)
                    # Map normalized back to original (keep first occurrence)
                    if normalized not in self._normalized_to_original:
                        self._normalized_to_original[normalized] = name

        logger.info(f"Built fuzzy cache with {len(self._customer_names_cache)} customer names")

    def match(self, transaction: Transaction) -> Optional[MatchResult]:
        """
        Attempt to match transaction using fuzzy name matching

        Args:
            transaction: Transaction to match

        Returns:
            MatchResult if match found above threshold, None otherwise
        """
        if not self.customer_loader or not self._normalized_names_cache:
            logger.warning("Customer loader not initialized or cache empty")
            return None

        # Extract potential customer name from transaction
        search_texts = self._extract_search_texts(transaction)

        best_match_original = None
        best_score = 0
        match_method_detail = ""

        for search_text in search_texts:
            if not search_text or len(search_text) < 3:
                continue

            # Normalize the search text
            normalized_search = normalize_company_name(search_text)
            if not normalized_search or len(normalized_search) < 2:
                continue

            # Method 1: Direct ratio on normalized names (best for full names)
            matches = process.extract(
                normalized_search,
                self._normalized_names_cache,
                scorer=fuzz.ratio,
                limit=5
            )

            for norm_match, score, _ in matches:
                if score > best_score and score >= self.MIN_MATCH_THRESHOLD:
                    # Get original name from normalized
                    original = self._normalized_to_original.get(norm_match, "")
                    if original:
                        best_score = score
                        best_match_original = original
                        match_method_detail = f"normalized ratio={score:.0f}%"

            # Method 2: Partial ratio for truncated bank names (fallback)
            if best_score < self.HIGH_CONFIDENCE_THRESHOLD:
                partial_matches = process.extract(
                    normalized_search,
                    self._normalized_names_cache,
                    scorer=fuzz.partial_ratio,
                    limit=5
                )

                for norm_match, score, _ in partial_matches:
                    # Partial ratio needs higher threshold to avoid false positives
                    adjusted_score = score * 0.9  # Slight penalty for partial match
                    if adjusted_score > best_score and adjusted_score >= self.MIN_MATCH_THRESHOLD:
                        original = self._normalized_to_original.get(norm_match, "")
                        if original:
                            best_score = adjusted_score
                            best_match_original = original
                            match_method_detail = f"partial ratio={score:.0f}%"

        if not best_match_original:
            return None

        # Get customer code
        customer_code = self._name_to_code.get(best_match_original.upper(), "")
        if not customer_code:
            return None

        # Determine confidence level
        if best_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence_level = ConfidenceLevel.HIGH
        elif best_score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        # Get alternative matches
        alternatives = self._get_alternatives(search_texts[0] if search_texts else "", best_match_original)

        # Normalize score to 0-1 range
        normalized_score = best_score / 100.0

        return MatchResult(
            customer_code=customer_code,
            customer_name=best_match_original,
            confidence_score=normalized_score,
            confidence_level=confidence_level,
            match_method=MatchMethod.LAYER_3_FUZZY_NAME,
            invoice_allocations=[],
            match_details=f"Fuzzy match: {match_method_detail}",
            alternative_matches=alternatives
        )

    def _extract_search_texts(self, transaction: Transaction) -> List[str]:
        """Extract potential customer names from transaction fields"""
        texts = []

        # Transaction detail often contains customer name
        detail = transaction.transaction_detail
        if detail:
            # Take first part before common separators
            for sep in ['SI-', 'SI ', '/', '\\', '  ']:
                if sep in detail:
                    detail = detail.split(sep)[0]
            texts.append(detail.strip())

        # Customer reference might have name
        ref = transaction.customer_reference
        if ref:
            # Clean up reference
            ref_clean = ref.strip()
            # Skip if it's just numbers or very short
            if not ref_clean.isdigit() and len(ref_clean) > 3:
                texts.append(ref_clean)

        # Combined for broader matching
        if transaction.transaction_detail and transaction.customer_reference:
            texts.append(f"{transaction.transaction_detail} {transaction.customer_reference}")

        return texts

    def _get_alternatives(self, search_text: str, exclude_name: str) -> List[dict]:
        """Get alternative matches for user review"""
        if not search_text:
            return []

        alternatives = []
        normalized_search = normalize_company_name(search_text)

        if not normalized_search:
            return []

        # Find alternatives using normalized matching
        matches = process.extract(
            normalized_search,
            self._normalized_names_cache,
            scorer=fuzz.ratio,
            limit=10
        )

        for norm_match, score, _ in matches:
            original = self._normalized_to_original.get(norm_match, "")
            if original and original != exclude_name and score >= self.MIN_MATCH_THRESHOLD:
                code = self._name_to_code.get(original.upper(), "")
                if code:
                    alternatives.append({
                        "customer_code": code,
                        "customer_name": original,
                        "score": score / 100.0
                    })

        return alternatives[:3]

    def get_stats(self) -> dict:
        """Get matcher statistics"""
        return {
            "layer": 3,
            "name": "Fuzzy Name Matching",
            "loaded": self.customer_loader is not None,
            "cached_names": len(self._customer_names_cache),
            "thresholds": {
                "high": self.HIGH_CONFIDENCE_THRESHOLD,
                "medium": self.MEDIUM_CONFIDENCE_THRESHOLD,
                "min": self.MIN_MATCH_THRESHOLD
            }
        }
