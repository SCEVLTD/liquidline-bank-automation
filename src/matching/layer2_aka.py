"""
Liquidline Bank Reconciliation Automation
Layer 2: AKA Sheet Pattern Matcher

Uses the 551-entry AKA sheet to match bank references
to customer codes based on known patterns.

Coverage: ~25% of transactions
Accuracy: ~95%
"""

from typing import Optional
import logging

from ..models.transaction import (
    Transaction, MatchResult, ConfidenceLevel, MatchMethod
)
from ..data.aka_loader import AKALoader

logger = logging.getLogger(__name__)


class AKAMatcher:
    """
    Layer 2 Matcher: AKA Sheet Pattern Lookup

    The AKA sheet contains 551 known mappings of bank reference
    patterns to customer codes. This is maintained manually by
    the finance team based on historical patterns.

    Examples:
    - "LIQLIN001" -> Customer FREIGHTLINER LTD
    - "GROUP 1 JLR" -> Customer GROUP1 RETAIL
    - "MOTORRAD WELWYN GC" -> Customer LIND MOTORRAD LIMI
    """

    def __init__(self, aka_loader: Optional[AKALoader] = None):
        """
        Args:
            aka_loader: Loaded AKA data, or None to load later
        """
        self.aka_loader = aka_loader

    def set_loader(self, aka_loader: AKALoader):
        """Set the AKA loader after initialization"""
        self.aka_loader = aka_loader

    def match(self, transaction: Transaction) -> Optional[MatchResult]:
        """
        Attempt to match transaction using AKA patterns

        Args:
            transaction: Transaction to match

        Returns:
            MatchResult if match found, None otherwise
        """
        if not self.aka_loader:
            logger.warning("AKA loader not initialized")
            return None

        # Try customer reference first, then transaction detail
        search_texts = [
            transaction.customer_reference,
            transaction.transaction_detail,
            # Also try combined
            f"{transaction.customer_reference} {transaction.transaction_detail}"
        ]

        best_match = None
        best_score = 0.0

        for text in search_texts:
            if not text or text.strip().lower() == 'nan':
                continue

            result = self.aka_loader.find_match(text)
            if result:
                pattern, score = result
                if score > best_score:
                    best_score = score
                    best_match = pattern

        if not best_match:
            return None

        # Determine confidence level based on score
        if best_score >= 0.90:
            confidence_level = ConfidenceLevel.HIGH
        elif best_score >= 0.70:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        # Get alternative matches for user review
        alternatives = []
        for text in search_texts[:2]:  # Just ref and detail
            if text:
                alt_matches = self.aka_loader.find_all_matches(text, limit=3)
                for pattern, score in alt_matches:
                    if pattern.customer_code != best_match.customer_code:
                        alternatives.append({
                            "customer_code": pattern.customer_code,
                            "customer_name": pattern.customer_name,
                            "pattern": pattern.pattern,
                            "score": score
                        })

        return MatchResult(
            customer_code=best_match.customer_code,
            customer_name=best_match.customer_name,
            confidence_score=best_score,
            confidence_level=confidence_level,
            match_method=MatchMethod.LAYER_2_AKA_PATTERN,
            invoice_allocations=[],  # AKA doesn't provide invoice info
            match_details=f"Matched via AKA pattern: '{best_match.pattern}'",
            alternative_matches=alternatives[:3]  # Top 3 alternatives
        )

    def get_stats(self) -> dict:
        """Get matcher statistics"""
        stats = {
            "layer": 2,
            "name": "AKA Pattern Lookup",
            "loaded": self.aka_loader is not None
        }

        if self.aka_loader:
            stats.update(self.aka_loader.get_summary())

        return stats
