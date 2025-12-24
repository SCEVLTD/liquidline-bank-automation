"""
Liquidline Bank Reconciliation Automation
Matching Orchestrator

Coordinates the 4-layer matching system and manages
the overall matching workflow.
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..models.transaction import (
    Transaction, MatchResult, ConfidenceLevel, MatchMethod
)
from ..data.customer_loader import CustomerLoader
from ..data.aka_loader import AKALoader
from .layer1_si import SIInvoiceMatcher
from .layer2_aka import AKAMatcher
from .layer3_fuzzy import FuzzyMatcher
from .layer4_ai import AIMatcher

logger = logging.getLogger(__name__)


class MatchingOrchestrator:
    """
    Orchestrates the 4-layer matching system

    Processing order:
    1. Layer 1: SI Invoice Pattern (highest accuracy)
    2. Layer 2: AKA Sheet Pattern (known mappings)
    3. Layer 3: Fuzzy Name Match (customer database)
    4. Layer 4: AI Inference (fallback for ambiguous)

    Each layer is tried in order. If a layer returns a HIGH confidence
    match, processing stops. Otherwise, continues to next layer.
    """

    def __init__(
        self,
        customer_loader: Optional[CustomerLoader] = None,
        aka_loader: Optional[AKALoader] = None,
        api_key: Optional[str] = None,
        ai_provider: str = "openrouter"
    ):
        """
        Initialize the orchestrator with data sources

        Args:
            customer_loader: Customer master data
            aka_loader: AKA pattern sheet data
            api_key: API key for LLM (Layer 4)
            ai_provider: "openrouter" or "anthropic"
        """
        self.customer_loader = customer_loader
        self.aka_loader = aka_loader

        # Initialize matchers
        self.layer1 = SIInvoiceMatcher()
        self.layer2 = AKAMatcher(aka_loader)
        self.layer3 = FuzzyMatcher(customer_loader)
        self.layer4 = AIMatcher(api_key=api_key, provider=ai_provider)

        # If loaders provided, configure matchers
        if customer_loader:
            self.layer3.set_loader(customer_loader)
        if aka_loader:
            self.layer2.set_loader(aka_loader)

        # Statistics
        self.stats = {
            "total_processed": 0,
            "layer1_matches": 0,
            "layer2_matches": 0,
            "layer3_matches": 0,
            "layer4_matches": 0,
            "unmatched": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0
        }

    def set_customer_loader(self, loader: CustomerLoader):
        """Set customer loader after initialization"""
        self.customer_loader = loader
        self.layer3.set_loader(loader)

    def set_aka_loader(self, loader: AKALoader):
        """Set AKA loader after initialization"""
        self.aka_loader = loader
        self.layer2.set_loader(loader)

    def match_transaction(self, transaction: Transaction) -> Transaction:
        """
        Process a single transaction through the matching layers

        Args:
            transaction: Transaction to match

        Returns:
            Transaction with match_result populated
        """
        self.stats["total_processed"] += 1

        # Skip non-processable transactions
        if not transaction.is_processable:
            return transaction

        # Try each layer in order
        match_result = None

        # Layer 1: SI Invoice Pattern
        match_result = self.layer1.match(transaction)
        if match_result and match_result.confidence_level == ConfidenceLevel.HIGH:
            self.stats["layer1_matches"] += 1
            transaction.match_result = match_result
            self._update_confidence_stats(match_result)
            return transaction

        # Layer 2: AKA Pattern
        layer2_result = self.layer2.match(transaction)
        if layer2_result:
            if not match_result or layer2_result.confidence_score > match_result.confidence_score:
                match_result = layer2_result

            if match_result.confidence_level == ConfidenceLevel.HIGH:
                self.stats["layer2_matches"] += 1
                transaction.match_result = match_result
                self._update_confidence_stats(match_result)
                return transaction

        # Layer 3: Fuzzy Name Match
        layer3_result = self.layer3.match(transaction)
        if layer3_result:
            if not match_result or layer3_result.confidence_score > match_result.confidence_score:
                match_result = layer3_result

            if match_result.confidence_level == ConfidenceLevel.HIGH:
                self.stats["layer3_matches"] += 1
                transaction.match_result = match_result
                self._update_confidence_stats(match_result)
                return transaction

        # Layer 4: AI Inference (only if we have candidates)
        if self.customer_loader and match_result and match_result.confidence_level != ConfidenceLevel.HIGH:
            # Get candidate customers for AI to consider
            candidates = self._get_ai_candidates(transaction, match_result)
            if candidates:
                layer4_result = self.layer4.match(transaction, candidates)
                if layer4_result:
                    if not match_result or layer4_result.confidence_score > match_result.confidence_score:
                        match_result = layer4_result
                        self.stats["layer4_matches"] += 1

        # Assign best match found
        if match_result:
            transaction.match_result = match_result
            self._update_confidence_stats(match_result)
        else:
            self.stats["unmatched"] += 1

        transaction.processed_at = datetime.now()
        return transaction

    def match_transactions(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Process multiple transactions through matching

        Args:
            transactions: List of transactions to process

        Returns:
            List of transactions with match_result populated
        """
        logger.info(f"Processing {len(transactions)} transactions through matching engine")

        results = []
        for i, transaction in enumerate(transactions):
            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{len(transactions)} transactions")

            matched = self.match_transaction(transaction)
            results.append(matched)

        logger.info(f"Matching complete. Stats: {self.get_stats()}")
        return results

    def _get_ai_candidates(self, transaction: Transaction, current_match: Optional[MatchResult]) -> List[dict]:
        """Get candidate customers for AI matching"""
        candidates = []

        # Add current match alternatives
        if current_match and current_match.alternative_matches:
            candidates.extend(current_match.alternative_matches)

        # Add fuzzy search results
        if self.customer_loader:
            search_text = transaction.transaction_detail or transaction.customer_reference
            if search_text:
                fuzzy_results = self.customer_loader.search_customers(search_text, limit=10)
                for customer in fuzzy_results:
                    candidates.append({
                        "code": customer.get("code", ""),
                        "name": customer.get("name", "")
                    })

        # Deduplicate by code
        seen_codes = set()
        unique_candidates = []
        for c in candidates:
            code = c.get("code") or c.get("customer_code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_candidates.append({
                    "code": code,
                    "name": c.get("name") or c.get("customer_name", "")
                })

        return unique_candidates[:20]  # Limit for API

    def _update_confidence_stats(self, match_result: MatchResult):
        """Update confidence level statistics"""
        if match_result.confidence_level == ConfidenceLevel.HIGH:
            self.stats["high_confidence"] += 1
        elif match_result.confidence_level == ConfidenceLevel.MEDIUM:
            self.stats["medium_confidence"] += 1
        else:
            self.stats["low_confidence"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get matching statistics"""
        total = self.stats["total_processed"]
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "match_rate": (total - self.stats["unmatched"]) / total * 100,
            "high_confidence_rate": self.stats["high_confidence"] / total * 100,
            "layer_breakdown": {
                "layer1_pct": self.stats["layer1_matches"] / total * 100,
                "layer2_pct": self.stats["layer2_matches"] / total * 100,
                "layer3_pct": self.stats["layer3_matches"] / total * 100,
                "layer4_pct": self.stats["layer4_matches"] / total * 100,
            }
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "total_processed": 0,
            "layer1_matches": 0,
            "layer2_matches": 0,
            "layer3_matches": 0,
            "layer4_matches": 0,
            "unmatched": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0
        }
