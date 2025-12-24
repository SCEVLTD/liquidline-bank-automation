"""
Liquidline Bank Reconciliation Automation
Layer 1: SI Invoice Pattern Matcher

Extracts SI-XXXXXX invoice numbers from bank references
and matches to customers via invoice lookup.

This is the highest confidence matcher (~100% accuracy when pattern found)
"""

import re
from typing import List, Optional, Tuple
import logging

from ..models.transaction import (
    Transaction, MatchResult, InvoiceAllocation,
    ConfidenceLevel, MatchMethod
)

logger = logging.getLogger(__name__)


class SIInvoiceMatcher:
    """
    Layer 1 Matcher: SI Invoice Pattern Extraction

    Handles patterns like:
    - "SI-794931" (standard format)
    - "SI794931" (no hyphen)
    - "SI 794931" (space)
    - "SI-789361  SI-7893..." (multiple invoices)
    - "SI787264-SI788064" (range/multiple)
    - "2748699/SI-78696" (mixed reference)

    Coverage: ~23% of transactions
    Accuracy: ~100% when pattern found
    """

    # Regex patterns for SI invoice numbers
    SI_PATTERNS = [
        r'SI[-\s]?(\d{5,7})',           # SI-123456 or SI 123456 or SI123456
        r'SI(\d{5,7})',                  # SI123456 (no separator)
    ]

    def __init__(self, invoice_lookup_func=None, customer_lookup_func=None):
        """
        Args:
            invoice_lookup_func: Function to lookup customer from invoice number
                                 Signature: (invoice_number: str) -> Optional[dict]
                                 Returns: {"customer_code": str, "customer_name": str, "amount": float}
            customer_lookup_func: Function to lookup customer details
                                  Signature: (customer_code: str) -> Optional[dict]
        """
        self.invoice_lookup = invoice_lookup_func
        self.customer_lookup = customer_lookup_func
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SI_PATTERNS]

    def extract_invoice_numbers(self, text: str) -> List[str]:
        """
        Extract all SI invoice numbers from text

        Args:
            text: Bank reference or transaction detail

        Returns:
            List of invoice numbers (without SI- prefix, just digits)
        """
        if not text:
            return []

        invoice_numbers = set()

        for pattern in self._compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # Normalize to standard format
                invoice_num = match.strip()
                if invoice_num:
                    invoice_numbers.add(f"SI-{invoice_num}")

        return sorted(list(invoice_numbers))

    def match(self, transaction: Transaction) -> Optional[MatchResult]:
        """
        Attempt to match transaction using SI invoice patterns

        Args:
            transaction: Transaction to match

        Returns:
            MatchResult if match found, None otherwise
        """
        # Try customer reference first, then transaction detail
        search_texts = [
            transaction.customer_reference,
            transaction.transaction_detail
        ]

        all_invoices = []
        for text in search_texts:
            invoices = self.extract_invoice_numbers(text)
            all_invoices.extend(invoices)

        # Remove duplicates while preserving order
        seen = set()
        unique_invoices = []
        for inv in all_invoices:
            if inv not in seen:
                seen.add(inv)
                unique_invoices.append(inv)

        if not unique_invoices:
            return None

        logger.debug(f"Found invoice numbers: {unique_invoices}")

        # If we have invoice lookup capability, use it
        if self.invoice_lookup:
            return self._match_with_lookup(transaction, unique_invoices)

        # Otherwise, return match with invoice numbers but no customer yet
        return self._create_basic_match(transaction, unique_invoices)

    def _match_with_lookup(self, transaction: Transaction, invoices: List[str]) -> Optional[MatchResult]:
        """Match using invoice lookup to find customer"""
        customer_code = None
        customer_name = None
        allocations = []

        for invoice_num in invoices:
            invoice_info = self.invoice_lookup(invoice_num)
            if invoice_info:
                if not customer_code:
                    customer_code = invoice_info.get("customer_code", "")
                    customer_name = invoice_info.get("customer_name", "")

                # Create allocation for this invoice
                allocation = InvoiceAllocation(
                    invoice_number=invoice_num,
                    invoice_amount=invoice_info.get("amount", 0),
                    allocated_amount=0,  # Will be calculated later
                )
                allocations.append(allocation)

        if not customer_code:
            # Invoice not found in system - still return partial match
            return self._create_basic_match(transaction, invoices)

        # Calculate allocations based on transaction amount
        if allocations:
            allocations = self._calculate_allocations(transaction.amount, allocations)

        return MatchResult(
            customer_code=customer_code,
            customer_name=customer_name,
            confidence_score=1.0,  # SI matches are 100% confident
            confidence_level=ConfidenceLevel.HIGH,
            match_method=MatchMethod.LAYER_1_SI_INVOICE,
            invoice_allocations=allocations,
            match_details=f"Matched via SI invoice pattern: {', '.join(invoices)}"
        )

    def _create_basic_match(self, transaction: Transaction, invoices: List[str]) -> MatchResult:
        """Create basic match when we have invoices but no lookup"""
        # Create placeholder allocations
        allocations = []
        for invoice_num in invoices:
            allocation = InvoiceAllocation(
                invoice_number=invoice_num,
                invoice_amount=0,  # Unknown
                allocated_amount=transaction.amount / len(invoices) if invoices else 0,
            )
            allocations.append(allocation)

        return MatchResult(
            customer_code="",  # To be looked up
            customer_name="",
            confidence_score=0.95,  # High but not perfect without lookup
            confidence_level=ConfidenceLevel.HIGH,
            match_method=MatchMethod.LAYER_1_SI_INVOICE,
            invoice_allocations=allocations,
            match_details=f"SI invoice pattern found: {', '.join(invoices)} (customer lookup pending)"
        )

    def _calculate_allocations(self, total_amount: float, allocations: List[InvoiceAllocation]) -> List[InvoiceAllocation]:
        """
        Calculate how to allocate payment across invoices

        Uses FIFO approach - allocate to invoices in order
        """
        remaining = total_amount

        for alloc in allocations:
            if remaining <= 0:
                alloc.allocated_amount = 0
            elif alloc.invoice_amount > 0:
                # Allocate up to invoice amount
                alloc.allocated_amount = min(remaining, alloc.invoice_amount)
                alloc.remaining_balance = alloc.invoice_amount - alloc.allocated_amount
                remaining -= alloc.allocated_amount
            else:
                # Unknown invoice amount - allocate proportionally
                alloc.allocated_amount = total_amount / len(allocations)

        return allocations

    def get_stats(self) -> dict:
        """Get matcher statistics"""
        return {
            "layer": 1,
            "name": "SI Invoice Pattern",
            "patterns": len(self.SI_PATTERNS),
            "has_invoice_lookup": self.invoice_lookup is not None
        }
