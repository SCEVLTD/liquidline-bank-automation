"""
Liquidline Bank Reconciliation Automation
Data Models for Transactions and Matching Results
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence levels for matching (Karen's color coding)"""
    HIGH = "high"       # GREEN - Auto-approve candidate
    MEDIUM = "medium"   # YELLOW - Review suggested match
    LOW = "low"         # RED - Exception queue


class MatchMethod(Enum):
    """Which matching layer produced the result"""
    LAYER_1_SI_INVOICE = "si_invoice"       # Exact SI-XXXXXX match
    LAYER_2_AKA_PATTERN = "aka_pattern"     # AKA sheet lookup
    LAYER_3_FUZZY_NAME = "fuzzy_name"       # Fuzzy customer name match
    LAYER_4_AI_INFERENCE = "ai_inference"   # Claude AI inference
    MANUAL = "manual"                        # Manual assignment
    UNMATCHED = "unmatched"                  # No match found


class TransactionType(Enum):
    """Bank transaction types"""
    BANK_GIRO_CREDIT = "Bank Giro Credit"
    FASTER_PAYMENT = "Faster Payment"
    CHAPS = "CHAPS"
    DIRECT_DEBIT = "Direct Debit"
    BACS = "BACS"
    OPENING_LEDGER = "Opening Ledger"
    CLOSING_LEDGER = "Closing Ledger"
    SWEEPING = "Sweeping"
    OTHER = "Other"


@dataclass
class InvoiceAllocation:
    """
    Represents allocation of payment to a specific invoice
    Critical for Karen's requirement - Step 2 of Eagle process
    """
    invoice_number: str              # SI-XXXXXX format
    invoice_amount: float            # Original invoice amount
    allocated_amount: float          # Amount allocated from this payment
    remaining_balance: float = 0.0   # Balance after allocation
    allocation_date: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "invoice_number": self.invoice_number,
            "invoice_amount": self.invoice_amount,
            "allocated_amount": self.allocated_amount,
            "remaining_balance": self.remaining_balance,
            "allocation_date": self.allocation_date.isoformat() if self.allocation_date else None
        }


@dataclass
class MatchResult:
    """
    Result of matching engine - contains customer match and invoice allocations
    """
    customer_code: str
    customer_name: str
    confidence_score: float                          # 0.0 to 1.0
    confidence_level: ConfidenceLevel               # HIGH/MEDIUM/LOW
    match_method: MatchMethod                       # Which layer matched
    invoice_allocations: List[InvoiceAllocation] = field(default_factory=list)
    match_details: str = ""                         # Human-readable explanation
    alternative_matches: List[dict] = field(default_factory=list)  # Other possible matches

    @property
    def total_allocated(self) -> float:
        """Total amount allocated across all invoices"""
        return sum(alloc.allocated_amount for alloc in self.invoice_allocations)

    def to_dict(self) -> dict:
        return {
            "customer_code": self.customer_code,
            "customer_name": self.customer_name,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "match_method": self.match_method.value,
            "invoice_allocations": [a.to_dict() for a in self.invoice_allocations],
            "match_details": self.match_details,
            "total_allocated": self.total_allocated
        }


@dataclass
class Transaction:
    """
    Represents a single bank transaction from Lloyds CSV
    """
    # Core transaction data (from bank CSV)
    row_id: int                          # Row number in source file
    post_date: datetime
    account_number: str
    account_name: str
    transaction_type: str
    amount: float
    customer_reference: str              # Key field for matching
    transaction_detail: str              # Secondary matching field
    balance: float

    # Matching results (populated by matching engine)
    match_result: Optional[MatchResult] = None

    # Processing status
    is_processed: bool = False
    is_posted: bool = False              # Posted to Eagle
    posted_reference: str = ""           # Eagle batch/posting reference

    # Exception handling
    is_exception: bool = False
    exception_type: str = ""
    exception_notes: str = ""

    # Audit trail
    source_file: str = ""
    processed_at: Optional[datetime] = None
    processed_by: str = ""

    @property
    def is_processable(self) -> bool:
        """Check if transaction should be processed (not opening/closing ledger)"""
        skip_types = ["Opening Ledger", "Closing Ledger", "Sweeping"]
        return self.transaction_type not in skip_types

    @property
    def confidence_level(self) -> Optional[ConfidenceLevel]:
        """Get confidence level from match result"""
        if self.match_result:
            return self.match_result.confidence_level
        return None

    @property
    def matched_customer(self) -> Optional[str]:
        """Get matched customer code"""
        if self.match_result:
            return self.match_result.customer_code
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for export"""
        return {
            "row_id": self.row_id,
            "post_date": self.post_date.strftime("%d/%m/%Y"),
            "account_number": self.account_number,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "customer_reference": self.customer_reference,
            "transaction_detail": self.transaction_detail,
            "balance": self.balance,
            "matched_customer_code": self.match_result.customer_code if self.match_result else "",
            "matched_customer_name": self.match_result.customer_name if self.match_result else "",
            "confidence_score": self.match_result.confidence_score if self.match_result else 0,
            "confidence_level": self.match_result.confidence_level.value if self.match_result else "unmatched",
            "match_method": self.match_result.match_method.value if self.match_result else "",
            "invoice_allocations": [a.to_dict() for a in self.match_result.invoice_allocations] if self.match_result else [],
            "is_exception": self.is_exception,
            "exception_type": self.exception_type,
            "is_posted": self.is_posted,
            "posted_reference": self.posted_reference
        }

    def __repr__(self) -> str:
        return f"Transaction({self.post_date.strftime('%d/%m/%Y')}, £{self.amount:.2f}, {self.customer_reference[:30]}...)"
