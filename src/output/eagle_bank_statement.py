"""
Eagle Bank Statement Export Generator

Generates CSV files in the exact format Eagle expects for Bank Statement import.
Based on Bank Reconciliation Settings discovered in Eagle:
- Column A: Date
- Column B: Type (optional)
- Column C: Reference
- Column D: Received (credits/money in)
- Column E: Paid (debits/money out)
- Column F: Balance (optional)

Settings: 1 header row, Auto Reconcile ON, Match on Amount Only ON
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd


def generate_eagle_bank_statement(
    transactions: List[Dict],
    output_path: str,
    bank_code: str = "LL01",
    include_balance: bool = False,
    include_type: bool = True
) -> str:
    """
    Generate a CSV file in Eagle's Bank Statement import format.

    Args:
        transactions: List of transaction dicts with keys:
            - date: Transaction date (datetime or string)
            - reference: Bank reference
            - amount: Transaction amount (positive = credit, negative = debit)
            - type: Optional transaction type
            - customer_code: Matched customer code (for reference)
            - customer_name: Matched customer name (for reference)
        output_path: Path to save the CSV file
        bank_code: Bank code (LL01, LL02, etc.)
        include_balance: Whether to include running balance column
        include_type: Whether to include type column

    Returns:
        Path to the generated file
    """
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build rows
    rows = []
    running_balance = 0.0

    for txn in transactions:
        # Parse date
        date_val = txn.get('date', '')
        if isinstance(date_val, datetime):
            date_str = date_val.strftime('%d/%m/%Y')
        else:
            date_str = str(date_val)

        # Parse amount - positive = received (credit), negative = paid (debit)
        amount = float(txn.get('amount', 0))

        if amount >= 0:
            received = f"{amount:.2f}"
            paid = ""
            running_balance += amount
        else:
            received = ""
            paid = f"{abs(amount):.2f}"
            running_balance -= abs(amount)

        # Build reference - include customer code if matched
        reference = txn.get('reference', txn.get('transaction_detail', ''))
        customer_code = txn.get('customer_code', '')
        if customer_code:
            reference = f"{reference} [{customer_code}]"

        row = {
            'Date': date_str,
            'Reference': reference[:50],  # Truncate if too long
            'Received': received,
            'Paid': paid,
        }

        if include_type:
            row['Type'] = txn.get('type', 'BGC')  # BGC = Bank Giro Credit

        if include_balance:
            row['Balance'] = f"{running_balance:.2f}"

        rows.append(row)

    # Define column order based on Eagle settings
    if include_type and include_balance:
        columns = ['Date', 'Type', 'Reference', 'Received', 'Paid', 'Balance']
    elif include_type:
        columns = ['Date', 'Type', 'Reference', 'Received', 'Paid']
    elif include_balance:
        columns = ['Date', 'Reference', 'Received', 'Paid', 'Balance']
    else:
        columns = ['Date', 'Reference', 'Received', 'Paid']

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            # Filter to only include columns we want
            filtered_row = {k: row.get(k, '') for k in columns}
            writer.writerow(filtered_row)

    return output_path


def generate_eagle_bank_statement_from_df(
    df: pd.DataFrame,
    output_path: str,
    date_col: str = 'Posting Date',
    amount_col: str = 'Debit Amount',
    reference_col: str = 'Transaction Detail',
    customer_code_col: str = 'customer_code',
    bank_code: str = "LL01"
) -> str:
    """
    Generate Eagle Bank Statement from a pandas DataFrame.

    Args:
        df: DataFrame with bank transactions and match results
        output_path: Path to save the CSV
        date_col: Column name for date
        amount_col: Column name for amount
        reference_col: Column name for reference/description
        customer_code_col: Column name for matched customer code
        bank_code: Bank code for Eagle

    Returns:
        Path to generated file
    """
    transactions = []

    for _, row in df.iterrows():
        txn = {
            'date': row.get(date_col, ''),
            'amount': float(row.get(amount_col, 0)),
            'reference': str(row.get(reference_col, '')),
            'customer_code': str(row.get(customer_code_col, '')),
            'customer_name': str(row.get('customer_name', '')),
            'type': 'BGC' if float(row.get(amount_col, 0)) >= 0 else 'BP'
        }
        transactions.append(txn)

    return generate_eagle_bank_statement(
        transactions=transactions,
        output_path=output_path,
        bank_code=bank_code
    )


def generate_matched_receipts_for_eagle(
    matched_transactions: List,
    output_path: str,
    bank_code: str = "LL01"
) -> str:
    """
    Generate Eagle Bank Statement from matched Transaction objects.

    This is the primary function to use with our matching engine output.

    Args:
        matched_transactions: List of Transaction objects with match_result
        output_path: Path to save the CSV
        bank_code: Bank code (LL01 = Liquidline Current Account)

    Returns:
        Path to generated file
    """
    transactions = []

    for txn in matched_transactions:
        # Only include credit transactions (money in)
        if txn.amount <= 0:
            continue

        # Get match info
        customer_code = ''
        customer_name = ''
        if txn.match_result:
            customer_code = txn.match_result.customer_code or ''
            customer_name = txn.match_result.customer_name or ''

        # Build reference with customer code for easy identification
        reference = txn.transaction_detail or txn.customer_reference or ''
        if customer_code:
            # Append customer code for Eagle to help with allocation
            reference = f"{customer_code}: {reference}"[:50]

        transactions.append({
            'date': txn.post_date,  # FIXED: was txn.date (AttributeError)
            'amount': txn.amount,
            'reference': reference,
            'customer_code': customer_code,
            'customer_name': customer_name,
            'type': 'BGC'  # Bank Giro Credit
        })

    return generate_eagle_bank_statement(
        transactions=transactions,
        output_path=output_path,
        bank_code=bank_code,
        include_type=True,
        include_balance=False
    )


# Example usage and test
if __name__ == "__main__":
    # Test data
    test_transactions = [
        {
            'date': datetime(2025, 11, 21),
            'amount': 831.96,
            'reference': 'Group 1 Toyota Nottingham',
            'customer_code': 'L0118',
            'type': 'BGC'
        },
        {
            'date': datetime(2025, 11, 21),
            'amount': 1643.02,
            'reference': 'LEVC Payment SI-794819 SI-795304',
            'customer_code': '22979',
            'type': 'BGC'
        },
        {
            'date': datetime(2025, 11, 21),
            'amount': -500.00,
            'reference': 'Supplier payment',
            'customer_code': '',
            'type': 'BP'
        },
    ]

    output = generate_eagle_bank_statement(
        test_transactions,
        'output/test_eagle_bank_statement.csv'
    )
    print(f"Generated: {output}")

    # Show contents
    with open(output, 'r') as f:
        print(f.read())
