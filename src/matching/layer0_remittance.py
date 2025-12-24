"""
Layer 0: Remittance Matching - Highest confidence layer
Matches bank transactions to remittance advice documents.
Provides exact customer + invoice allocation.
"""

import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .remittance_parser import RemittanceParser, ParsedRemittance


@dataclass
class RemittanceMatch:
    """Result of remittance matching"""
    customer_code: str
    customer_name: str
    confidence: float
    invoices: List[str]  # Invoice numbers
    total_amount: float
    account_reference: Optional[str]
    remittance_file: Optional[str]
    method: str = "remittance"


class Layer0RemittanceMatcher:
    """
    Matches bank transactions against remittance advice documents.

    This is the highest-priority matching layer because remittances
    contain exact customer and invoice information.
    """

    def __init__(
        self,
        remittance_folder: Optional[str] = None,
        customer_lookup: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the remittance matcher.

        Args:
            remittance_folder: Path to folder containing remittance PDFs
            customer_lookup: Dict mapping account references to customer codes
        """
        self.parser = RemittanceParser()
        self.remittance_folder = remittance_folder
        self.customer_lookup = customer_lookup or {}
        self.parsed_remittances: List[Tuple[ParsedRemittance, str]] = []

    def load_remittances(self, folder: Optional[str] = None) -> int:
        """
        Load and parse all remittance PDFs from a folder.

        Returns:
            Number of remittances loaded
        """
        folder = folder or self.remittance_folder
        if not folder or not os.path.exists(folder):
            return 0

        self.parsed_remittances = []
        folder_path = Path(folder)

        for pdf_file in folder_path.glob("*.pdf"):
            try:
                remittance = self.parser.parse_pdf(str(pdf_file))
                if remittance.total_amount > 0:
                    self.parsed_remittances.append((remittance, str(pdf_file)))
            except Exception as e:
                print(f"Error parsing {pdf_file}: {e}")

        return len(self.parsed_remittances)

    def add_remittance_text(self, text: str, source: str = "manual") -> ParsedRemittance:
        """Add a remittance from raw text (e.g., email body)"""
        remittance = self.parser.parse_text(text)
        self.parsed_remittances.append((remittance, source))
        return remittance

    def match(
        self,
        amount: float,
        transaction_detail: str = "",
        date: str = "",
        tolerance: float = 0.01
    ) -> Optional[RemittanceMatch]:
        """
        Match a bank transaction against loaded remittances.

        Args:
            amount: Transaction amount (positive)
            transaction_detail: Bank transaction description
            date: Transaction date (for filtering)
            tolerance: Amount matching tolerance

        Returns:
            RemittanceMatch if found, None otherwise
        """
        amount = abs(amount)

        for remittance, source in self.parsed_remittances:
            # Check amount match
            if abs(remittance.total_amount - amount) <= tolerance:
                # Found a match!
                customer_code = self._resolve_customer_code(remittance)

                return RemittanceMatch(
                    customer_code=customer_code,
                    customer_name=remittance.customer_name,
                    confidence=min(0.99, remittance.confidence + 0.1),  # Boost confidence
                    invoices=[inv.invoice_number for inv in remittance.invoices],
                    total_amount=remittance.total_amount,
                    account_reference=remittance.account_reference,
                    remittance_file=source,
                    method="remittance"
                )

        return None

    def _resolve_customer_code(self, remittance: ParsedRemittance) -> str:
        """
        Resolve the Eagle customer code from remittance data.

        Tries:
        1. Account reference in remittance (e.g., L0118, LIQU001)
        2. Lookup table mapping company names to codes
        3. Empty string if unknown
        """
        # Check if account reference is in our lookup
        if remittance.account_reference:
            ref = remittance.account_reference.upper()
            if ref in self.customer_lookup:
                return self.customer_lookup[ref]
            # Account reference might BE the customer code
            if ref.isdigit() or (len(ref) <= 10 and ref[0].isalpha()):
                return ref

        # Try customer name lookup
        name_key = remittance.customer_name.upper().strip()
        if name_key in self.customer_lookup:
            return self.customer_lookup[name_key]

        return ""

    def get_invoice_allocation(self, match: RemittanceMatch) -> List[Dict]:
        """
        Get the invoice allocation breakdown for a match.

        Returns list of {invoice_number, amount} for Eagle posting.
        """
        for remittance, _ in self.parsed_remittances:
            if remittance.total_amount == match.total_amount:
                return [
                    {
                        "invoice_number": inv.invoice_number,
                        "amount": inv.amount,
                        "description": inv.description
                    }
                    for inv in remittance.invoices
                ]
        return []

    def get_stats(self) -> Dict:
        """Get statistics about loaded remittances"""
        if not self.parsed_remittances:
            return {
                "loaded": 0,
                "total_value": 0,
                "avg_confidence": 0
            }

        total_value = sum(r.total_amount for r, _ in self.parsed_remittances)
        avg_confidence = sum(r.confidence for r, _ in self.parsed_remittances) / len(self.parsed_remittances)

        return {
            "loaded": len(self.parsed_remittances),
            "total_value": total_value,
            "avg_confidence": avg_confidence,
            "customers": list(set(r.customer_name for r, _ in self.parsed_remittances))
        }


# Convenience function for integration
def create_remittance_matcher(
    remittance_folder: str,
    customers_df=None
) -> Layer0RemittanceMatcher:
    """
    Create a remittance matcher with customer lookup from DataFrame.

    Args:
        remittance_folder: Path to remittance PDFs
        customers_df: DataFrame with customer data (code, name columns)
    """
    lookup = {}

    if customers_df is not None:
        for _, row in customers_df.iterrows():
            code = str(row.get('code', row.get('Code', ''))).strip()
            name = str(row.get('name', row.get('Name', ''))).upper().strip()
            if code and name:
                lookup[name] = code

    matcher = Layer0RemittanceMatcher(
        remittance_folder=remittance_folder,
        customer_lookup=lookup
    )
    matcher.load_remittances()

    return matcher


if __name__ == "__main__":
    # Test with remittance examples
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    matcher = Layer0RemittanceMatcher(
        remittance_folder="remittance_examples"
    )

    loaded = matcher.load_remittances()
    print(f"Loaded {loaded} remittances")
    print(f"Stats: {matcher.get_stats()}")

    # Test matching
    test_amounts = [831.96, 1643.02, 360794.04, 1080.42]
    for amount in test_amounts:
        match = matcher.match(amount)
        if match:
            print(f"\n£{amount} -> {match.customer_name}")
            print(f"  Invoices: {match.invoices}")
            print(f"  Confidence: {match.confidence:.0%}")
