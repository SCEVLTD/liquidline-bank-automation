"""
Liquidline Bank Reconciliation Automation
Bank CSV Parser for Lloyds Bank Downloads

Handles the Lloyds CSV format with columns:
- Post Date, Account Number, Account Name, Type, Amount,
- Customer Reference, Transaction Detail, Balance
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Union
import logging

from ..models.transaction import Transaction

logger = logging.getLogger(__name__)


class BankParser:
    """
    Parser for Lloyds Bank CSV downloads

    Expected CSV format (8 columns):
    Post Date,Account Number,Account Name,Type,Amount,Customer Reference,Transaction Detail,Balance
    """

    EXPECTED_COLUMNS = [
        "Post Date",
        "Account Number",
        "Account Name",
        "Type",
        "Amount",
        "Customer Reference",
        "Transaction Detail",
        "Balance"
    ]

    # Transaction types to skip (not customer receipts)
    SKIP_TYPES = ["Opening Ledger", "Closing Ledger", "Sweeping"]

    def __init__(self):
        self.transactions: List[Transaction] = []
        self.source_file: str = ""
        self.parse_errors: List[dict] = []

    def parse_file(self, file_path: Union[str, Path]) -> List[Transaction]:
        """
        Parse a bank CSV file and return list of Transaction objects

        Args:
            file_path: Path to the CSV file

        Returns:
            List of Transaction objects (processable transactions only)
        """
        file_path = Path(file_path)
        self.source_file = file_path.name
        self.transactions = []
        self.parse_errors = []

        logger.info(f"Parsing bank file: {file_path.name}")

        try:
            # Read CSV with pandas
            df = pd.read_csv(
                file_path,
                encoding='utf-8',
                dtype=str,  # Read all as string initially
                na_values=['', 'NA', 'N/A'],
                keep_default_na=True
            )

            # Validate columns
            if not self._validate_columns(df):
                raise ValueError(f"Invalid column structure in {file_path.name}")

            # Parse each row
            for idx, row in df.iterrows():
                try:
                    transaction = self._parse_row(idx, row)
                    if transaction and transaction.is_processable:
                        self.transactions.append(transaction)
                except Exception as e:
                    self.parse_errors.append({
                        "row": idx + 2,  # +2 for header and 0-index
                        "error": str(e),
                        "data": row.to_dict()
                    })
                    logger.warning(f"Error parsing row {idx + 2}: {e}")

            logger.info(f"Parsed {len(self.transactions)} processable transactions from {file_path.name}")

            if self.parse_errors:
                logger.warning(f"Encountered {len(self.parse_errors)} parse errors")

            return self.transactions

        except Exception as e:
            logger.error(f"Failed to parse file {file_path.name}: {e}")
            raise

    def _validate_columns(self, df: pd.DataFrame) -> bool:
        """Validate that required columns exist"""
        missing = set(self.EXPECTED_COLUMNS) - set(df.columns)
        if missing:
            logger.error(f"Missing columns: {missing}")
            return False
        return True

    def _parse_row(self, idx: int, row: pd.Series) -> Optional[Transaction]:
        """
        Parse a single row into a Transaction object

        Args:
            idx: Row index
            row: Pandas Series representing the row

        Returns:
            Transaction object or None if row should be skipped
        """
        # Skip non-processable transaction types
        trans_type = str(row.get("Type", "")).strip()
        if trans_type in self.SKIP_TYPES:
            return None

        # Parse date
        date_str = str(row.get("Post Date", "")).strip()
        try:
            post_date = datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            # Try alternative format
            try:
                post_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}")

        # Parse amount
        amount_str = str(row.get("Amount", "0")).strip()
        amount_str = amount_str.replace(",", "").replace("£", "")
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError(f"Invalid amount: {amount_str}")

        # Parse balance
        balance_str = str(row.get("Balance", "0")).strip()
        balance_str = balance_str.replace(",", "").replace("£", "")
        try:
            balance = float(balance_str)
        except ValueError:
            balance = 0.0

        # Clean string fields
        customer_ref = str(row.get("Customer Reference", "")).strip()
        if customer_ref.lower() == "nan":
            customer_ref = ""

        trans_detail = str(row.get("Transaction Detail", "")).strip()
        if trans_detail.lower() == "nan":
            trans_detail = ""

        # Create Transaction object
        return Transaction(
            row_id=idx + 2,  # +2 for header and 0-index to match Excel row numbers
            post_date=post_date,
            account_number=str(row.get("Account Number", "")).strip(),
            account_name=str(row.get("Account Name", "")).strip(),
            transaction_type=trans_type,
            amount=amount,
            customer_reference=customer_ref,
            transaction_detail=trans_detail,
            balance=balance,
            source_file=self.source_file
        )

    def parse_multiple_files(self, file_paths: List[Union[str, Path]]) -> List[Transaction]:
        """
        Parse multiple bank CSV files

        Args:
            file_paths: List of paths to CSV files

        Returns:
            Combined list of Transaction objects from all files
        """
        all_transactions = []

        for file_path in file_paths:
            try:
                transactions = self.parse_file(file_path)
                all_transactions.extend(transactions)
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")

        # Sort by date
        all_transactions.sort(key=lambda t: (t.post_date, t.row_id))

        return all_transactions

    def get_summary(self) -> dict:
        """Get summary statistics of parsed transactions"""
        if not self.transactions:
            return {"total": 0}

        return {
            "total": len(self.transactions),
            "total_amount": sum(t.amount for t in self.transactions),
            "date_range": {
                "start": min(t.post_date for t in self.transactions).strftime("%d/%m/%Y"),
                "end": max(t.post_date for t in self.transactions).strftime("%d/%m/%Y")
            },
            "by_type": self._count_by_type(),
            "parse_errors": len(self.parse_errors),
            "source_file": self.source_file
        }

    def _count_by_type(self) -> dict:
        """Count transactions by type"""
        counts = {}
        for t in self.transactions:
            counts[t.transaction_type] = counts.get(t.transaction_type, 0) + 1
        return counts


# Convenience function
def parse_bank_file(file_path: Union[str, Path]) -> List[Transaction]:
    """Parse a single bank CSV file"""
    parser = BankParser()
    return parser.parse_file(file_path)
