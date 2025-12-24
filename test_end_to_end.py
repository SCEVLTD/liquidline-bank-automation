"""
End-to-End Test: Bank Reconciliation to Eagle Import
=====================================================
This script demonstrates the complete workflow:
1. Load bank transactions
2. Load customer master and AKA patterns
3. Load remittance PDFs
4. Match transactions through 5-layer system
5. Generate Eagle Bank Statement import file
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.models.transaction import Transaction, MatchResult, ConfidenceLevel
from src.data.customer_loader import CustomerLoader
from src.data.aka_loader import AKALoader
from src.matching.orchestrator import MatchingOrchestrator
from src.output.eagle_bank_statement import generate_eagle_bank_statement


def load_bank_transactions(csv_path: str) -> list:
    """Load bank transactions from CSV file"""
    df = pd.read_csv(csv_path)
    transactions = []

    for idx, row in df.iterrows():
        # Skip opening/closing ledger entries
        txn_type = str(row.get('Type', ''))
        if 'Ledger' in txn_type:
            continue

        # Parse amount
        amount = float(row.get('Amount', 0))

        # Skip debits (money out) for cash receipts matching
        # We're matching incoming payments
        if amount < 0:
            continue

        # Parse date
        date_str = str(row.get('Post Date', ''))
        try:
            post_date = datetime.strptime(date_str, '%d/%m/%Y')
        except:
            post_date = datetime.now()

        txn = Transaction(
            row_id=idx + 1,
            post_date=post_date,
            account_number=str(row.get('Account Number', '')),
            account_name=str(row.get('Account Name', '')),
            transaction_type=txn_type,
            amount=amount,
            customer_reference=str(row.get('Customer Reference', '')) if pd.notna(row.get('Customer Reference')) else '',
            transaction_detail=str(row.get('Transaction Detail', '')) if pd.notna(row.get('Transaction Detail')) else '',
            balance=float(row.get('Balance', 0)) if pd.notna(row.get('Balance')) else 0.0
        )
        transactions.append(txn)

    return transactions


def run_end_to_end_test():
    """Run the complete matching and export workflow"""

    print("=" * 60)
    print("LIQUIDLINE BANK RECONCILIATION - END-TO-END TEST")
    print("=" * 60)

    # Paths
    base_path = Path(__file__).parent
    bank_file = base_path / "data" / "21 Nov 25.csv"
    customer_file = base_path / "data" / "customer report.xlsx"
    aka_file = base_path / "data" / "ALL HISTORY 2024-2025.xlsx"
    remittance_folder = base_path / "remittance_examples"
    output_folder = base_path / "output"
    output_folder.mkdir(exist_ok=True)

    # Step 1: Load bank transactions
    print("\n[1/5] Loading bank transactions...")
    transactions = load_bank_transactions(str(bank_file))
    print(f"     Loaded {len(transactions)} credit transactions")

    # Step 2: Load customer master data
    print("\n[2/5] Loading customer master data...")
    customer_loader = None
    if customer_file.exists():
        customer_loader = CustomerLoader(str(customer_file))
        print(f"     Loaded {len(customer_loader.customers)} customers")
    else:
        print("     WARNING: Customer file not found, fuzzy matching disabled")

    # Step 3: Load AKA patterns
    print("\n[3/5] Loading AKA patterns...")
    aka_loader = None
    if aka_file.exists():
        aka_loader = AKALoader(str(aka_file))
        print(f"     Loaded {len(aka_loader.patterns)} AKA patterns")
    else:
        print("     WARNING: AKA file not found, pattern matching disabled")

    # Step 4: Initialize orchestrator and match
    print("\n[4/5] Running 5-layer matching engine...")
    orchestrator = MatchingOrchestrator(
        customer_loader=customer_loader,
        aka_loader=aka_loader,
        remittance_folder=str(remittance_folder) if remittance_folder.exists() else None
    )

    # Process transactions
    matched_transactions = orchestrator.match_transactions(transactions)

    # Get stats
    stats = orchestrator.get_stats()
    print(f"\n     MATCHING RESULTS:")
    print(f"     - Total processed: {stats['total_processed']}")
    print(f"     - Match rate: {stats.get('match_rate', 0):.1f}%")
    print(f"     - High confidence: {stats['high_confidence']}")
    print(f"     - Medium confidence: {stats['medium_confidence']}")
    print(f"     - Low confidence: {stats['low_confidence']}")
    print(f"     - Unmatched: {stats['unmatched']}")
    print(f"\n     LAYER BREAKDOWN:")
    print(f"     - Layer 0 (Remittance): {stats['layer0_matches']}")
    print(f"     - Layer 1 (SI Invoice): {stats['layer1_matches']}")
    print(f"     - Layer 2 (AKA Pattern): {stats['layer2_matches']}")
    print(f"     - Layer 3 (Fuzzy Name): {stats['layer3_matches']}")
    print(f"     - Layer 4 (AI): {stats['layer4_matches']}")

    # Step 5: Generate Eagle import file
    print("\n[5/5] Generating Eagle Bank Statement import file...")

    # Build transaction list for Eagle export
    eagle_transactions = []
    for txn in matched_transactions:
        customer_code = ''
        customer_name = ''

        if txn.match_result:
            customer_code = txn.match_result.customer_code or ''
            customer_name = txn.match_result.customer_name or ''

        # Build reference with match info
        reference = txn.transaction_detail or txn.customer_reference or ''
        if customer_code:
            reference = f"{customer_code}: {reference[:40]}"
        else:
            reference = reference[:50]

        eagle_transactions.append({
            'date': txn.post_date,
            'amount': txn.amount,
            'reference': reference,
            'customer_code': customer_code,
            'customer_name': customer_name,
            'type': 'BGC'  # Bank Giro Credit
        })

    # Generate the file
    output_file = output_folder / f"eagle_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generate_eagle_bank_statement(
        transactions=eagle_transactions,
        output_path=str(output_file),
        bank_code="LL01",
        include_type=True,
        include_balance=False
    )

    print(f"     Generated: {output_file}")

    # Show sample output
    print("\n" + "=" * 60)
    print("SAMPLE OUTPUT (first 10 rows):")
    print("=" * 60)

    df_output = pd.read_csv(output_file)
    print(df_output.head(10).to_string(index=False))

    # Summary of matched vs unmatched
    print("\n" + "=" * 60)
    print("MATCHED TRANSACTIONS SUMMARY:")
    print("=" * 60)

    matched_count = sum(1 for t in matched_transactions if t.match_result and t.match_result.customer_code)
    total_matched_value = sum(t.amount for t in matched_transactions if t.match_result and t.match_result.customer_code)
    total_value = sum(t.amount for t in matched_transactions)

    print(f"Transactions with customer match: {matched_count}/{len(matched_transactions)}")
    print(f"Value matched: £{total_matched_value:,.2f} / £{total_value:,.2f}")
    print(f"Match percentage by value: {(total_matched_value/total_value*100) if total_value > 0 else 0:.1f}%")

    # List high-value unmatched
    print("\n" + "-" * 60)
    print("HIGH-VALUE UNMATCHED (>£1000):")
    print("-" * 60)

    unmatched = [t for t in matched_transactions if not t.match_result or not t.match_result.customer_code]
    unmatched_high = [t for t in unmatched if t.amount > 1000]

    for t in sorted(unmatched_high, key=lambda x: -x.amount)[:10]:
        print(f"  £{t.amount:>10,.2f}  {(t.transaction_detail or t.customer_reference or 'N/A')[:50]}")

    print("\n" + "=" * 60)
    print(f"Eagle import file ready at: {output_file}")
    print("=" * 60)

    return str(output_file)


if __name__ == "__main__":
    run_end_to_end_test()
