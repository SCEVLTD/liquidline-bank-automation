"""
Liquidline Bank Reconciliation Automation
Customer Data Loader

Loads customer master data from Eagle export (customer report.xlsx)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class CustomerLoader:
    """
    Loader for Eagle customer master data

    This data is used for:
    - Validating customer codes during matching
    - Fuzzy name matching (Layer 3)
    - Looking up customer details for matched transactions
    """

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self.customers: Dict[str, dict] = {}  # Keyed by customer code
        self.customer_names: Dict[str, str] = {}  # name -> code lookup
        self.file_path = file_path
        self._loaded = False

        if file_path:
            self.load(file_path)

    def load(self, file_path: Union[str, Path]) -> int:
        """
        Load customer data from Excel file

        Args:
            file_path: Path to customer report xlsx

        Returns:
            Number of customers loaded
        """
        file_path = Path(file_path)
        logger.info(f"Loading customer data from: {file_path.name}")

        try:
            # Read Excel file - try to auto-detect structure
            df = pd.read_excel(file_path, engine='openpyxl')

            # Log columns found for debugging
            logger.info(f"Found columns: {list(df.columns)}")

            # Normalize column names (lowercase, strip whitespace)
            df.columns = df.columns.str.lower().str.strip()

            # Try to identify customer code and name columns
            code_col = self._find_column(df, ['customer code', 'code', 'customer_code', 'cust code', 'account code', 'account'])
            name_col = self._find_column(df, ['customer name', 'name', 'customer_name', 'cust name', 'account name'])

            if not code_col:
                # If no obvious code column, use first column
                code_col = df.columns[0]
                logger.warning(f"Using first column as customer code: {code_col}")

            if not name_col:
                # If no obvious name column, use second column
                name_col = df.columns[1] if len(df.columns) > 1 else code_col
                logger.warning(f"Using column as customer name: {name_col}")

            # Load customers
            skipped_header_rows = 0
            for idx, row in df.iterrows():
                code = str(row.get(code_col, "")).strip().upper()
                name = str(row.get(name_col, "")).strip()

                # Skip header/metadata rows
                if not code or code.lower() == 'nan':
                    skipped_header_rows += 1
                    continue

                # Skip rows that look like headers (DATE, ID, etc.)
                if code.startswith('DATE') or code == 'ID' or code.startswith('MASTER'):
                    skipped_header_rows += 1
                    continue

                # Skip if name is just column header text
                if name.lower() in ['account name', 'customer name', 'name', 'nan']:
                    skipped_header_rows += 1
                    continue

                self.customers[code] = {
                    "code": code,
                    "name": name,
                    "row_data": row.to_dict()
                }

                # Also store name -> code mapping for reverse lookup
                name_key = name.upper().strip()
                if name_key and name_key.lower() != 'nan':
                    self.customer_names[name_key] = code

            if skipped_header_rows > 0:
                logger.info(f"Skipped {skipped_header_rows} header/metadata rows")

            self._loaded = True
            logger.info(f"Loaded {len(self.customers)} customers")

            return len(self.customers)

        except Exception as e:
            logger.error(f"Failed to load customer data: {e}")
            raise

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find a column by checking multiple possible names"""
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    def get_customer(self, code: str) -> Optional[dict]:
        """Get customer by code"""
        return self.customers.get(code.upper().strip())

    def get_customer_by_name(self, name: str) -> Optional[dict]:
        """Get customer by exact name match"""
        code = self.customer_names.get(name.upper().strip())
        if code:
            return self.customers.get(code)
        return None

    def search_customers(self, query: str, limit: int = 10) -> List[dict]:
        """
        Search customers by partial name or code match

        Args:
            query: Search string
            limit: Maximum results to return

        Returns:
            List of matching customer dicts
        """
        query = query.upper().strip()
        results = []

        for code, customer in self.customers.items():
            if query in code or query in customer['name'].upper():
                results.append(customer)
                if len(results) >= limit:
                    break

        return results

    def get_all_customer_names(self) -> List[str]:
        """Get list of all customer names for fuzzy matching"""
        return [c['name'] for c in self.customers.values() if c['name']]

    def get_all_customer_codes(self) -> List[str]:
        """Get list of all customer codes"""
        return list(self.customers.keys())

    def get_summary(self) -> dict:
        """Get summary of loaded customer data"""
        return {
            "total_customers": len(self.customers),
            "loaded": self._loaded,
            "source_file": str(self.file_path) if self.file_path else None
        }

    def validate_code(self, code: str) -> bool:
        """Check if a customer code exists"""
        return code.upper().strip() in self.customers
