"""
Liquidline Bank Reconciliation Automation
Matching Orchestrator

Coordinates the 5-layer matching system and manages
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
from .layer0_remittance import Layer0RemittanceMatcher
from .layer1_si import SIInvoiceMatcher
from .layer2_aka import AKAMatcher
from .layer3_fuzzy import FuzzyMatcher
from .layer4_ai import AIMatcher

logger = logging.getLogger(__name__)


class MatchingOrchestrator:
    """
    Orchestrates the 5-layer matching system

    Processing order:
    0. Layer 0: Remittance Matching (highest priority - exact data from remittances)
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
        ai_provider: str = "openrouter",
        remittance_folder: Optional[str] = None
    ):
        """
        Initialize the orchestrator with data sources

        Args:
            customer_loader: Customer master data
            aka_loader: AKA pattern sheet data
            api_key: API key for LLM (Layer 4)
            ai_provider: "openrouter" or "anthropic"
            remittance_folder: Path to folder containing remittance PDFs
        """
        self.customer_loader = customer_loader
        self.aka_loader = aka_loader
        self.remittance_folder = remittance_folder

        # Initialize matchers
        self.layer0 = Layer0RemittanceMatcher(remittance_folder=remittance_folder)
        self.layer1 = SIInvoiceMatcher()
        self.layer2 = AKAMatcher(aka_loader)
        self.layer3 = FuzzyMatcher(customer_loader)
        self.layer4 = AIMatcher(api_key=api_key, provider=ai_provider)

        # If loaders provided, configure matchers
        if customer_loader:
            self.layer3.set_loader(customer_loader)
        if aka_loader:
            self.layer2.set_loader(aka_loader)

        # Load remittances if folder provided
        if remittance_folder:
            self.load_remittances(remittance_folder)

        # Statistics
        self.stats = {
            "total_processed": 0,
            "layer0_matches": 0,
            "layer1_matches": 0,
            "layer2_matches": 0,
            "layer3_matches": 0,
            "layer4_matches": 0,
            "unmatched": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            # NEW: Postable tracking (has customer_code = can be posted to Eagle)
            "postable": 0,  # Matches WITH customer code
            "needs_lookup": 0,  # Matches WITHOUT customer code (need manual lookup)
            "high_postable": 0  # High confidence AND has customer code
        }

    def set_customer_loader(self, loader: CustomerLoader):
        """Set customer loader after initialization"""
        self.customer_loader = loader
        self.layer3.set_loader(loader)

    def set_aka_loader(self, loader: AKALoader):
        """Set AKA loader after initialization"""
        self.aka_loader = loader
        self.layer2.set_loader(loader)

    def load_remittances(self, folder: str) -> int:
        """Load remittance PDFs from a folder"""
        count = self.layer0.load_remittances(folder)
        logger.info(f"Loaded {count} remittances from {folder}")
        return count

    def add_remittance_text(self, text: str, source: str = "manual"):
        """Add a remittance from text (e.g., email body)"""
        return self.layer0.add_remittance_text(text, source)

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

        # Layer 0: Remittance Matching (highest priority)
        remittance_match = self.layer0.match(
            amount=abs(transaction.amount),
            transaction_detail=transaction.transaction_detail or "",
            date=str(transaction.post_date) if transaction.post_date else ""
        )
        if remittance_match and remittance_match.confidence >= 0.85:
            # Create MatchResult from remittance
            from ..models.transaction import InvoiceAllocation
            invoice_allocations = [
                InvoiceAllocation(
                    invoice_number=inv_num,
                    invoice_amount=0.0,  # Unknown from remittance alone
                    allocated_amount=0.0
                ) for inv_num in remittance_match.invoices
            ]
            match_result = MatchResult(
                customer_code=remittance_match.customer_code,
                customer_name=remittance_match.customer_name,
                confidence_score=remittance_match.confidence,
                confidence_level=ConfidenceLevel.HIGH,
                match_method=MatchMethod.LAYER_1_SI_INVOICE,  # Treat as SI since we have invoices
                invoice_allocations=invoice_allocations,
                match_details=f"Matched via remittance: {remittance_match.remittance_file}"
            )
            self.stats["layer0_matches"] += 1
            transaction.match_result = match_result
            self._update_confidence_stats(match_result)
            return transaction

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

        # Track postable status (CRITICAL: only postable if we have customer_code)
        has_customer_code = bool(match_result.customer_code and match_result.customer_code.strip())
        if has_customer_code:
            self.stats["postable"] += 1
            if match_result.confidence_level == ConfidenceLevel.HIGH:
                self.stats["high_postable"] += 1
        else:
            self.stats["needs_lookup"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get matching statistics"""
        total = self.stats["total_processed"]
        if total == 0:
            return self.stats

        matched = total - self.stats["unmatched"]

        return {
            **self.stats,
            # Match rate = any match found (may or may not have customer code)
            "match_rate": matched / total * 100,
            "high_confidence_rate": self.stats["high_confidence"] / total * 100,
            # CRITICAL NEW METRICS: Postable rates (what actually can go to Eagle)
            "postable_rate": self.stats["postable"] / total * 100,
            "high_postable_rate": self.stats["high_postable"] / total * 100,
            "needs_lookup_rate": self.stats["needs_lookup"] / total * 100,
            # Layer breakdown
            "layer_breakdown": {
                "layer0_pct": self.stats["layer0_matches"] / total * 100,
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
            "layer0_matches": 0,
            "layer1_matches": 0,
            "layer2_matches": 0,
            "layer3_matches": 0,
            "layer4_matches": 0,
            "unmatched": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            # Postable tracking
            "postable": 0,
            "needs_lookup": 0,
            "high_postable": 0
        }
