"""
Liquidline Bank Reconciliation Automation
System Test Script

Tests the complete matching pipeline with real November 2025 data.
Run this to validate the system before deployment.
"""

import sys
import io
from pathlib import Path
from datetime import datetime
import logging

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import DATA_DIR, OUTPUT_DIR, AKA_SHEET_PATH, CUSTOMER_REPORT_PATH
from src.parsers.bank_parser import BankParser
from src.data.customer_loader import CustomerLoader
from src.data.aka_loader import AKALoader
from src.matching.orchestrator import MatchingOrchestrator
from src.matching.layer1_si import SIInvoiceMatcher
from src.output.excel_generator import ExcelGenerator
from src.models.transaction import ConfidenceLevel


def test_bank_parser():
    """Test the bank CSV parser"""
    print("\n" + "="*60)
    print("TEST 1: Bank CSV Parser")
    print("="*60)

    # Find test file
    test_file = DATA_DIR / "21 Nov 25.csv"
    if not test_file.exists():
        # Try alternative name
        test_file = DATA_DIR / "21 November 2025.csv"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return None

    parser = BankParser()
    transactions = parser.parse_file(test_file)

    print(f"✅ Parsed {len(transactions)} transactions from {test_file.name}")
    print(f"   Summary: {parser.get_summary()}")

    # Show sample transactions
    print("\n   Sample transactions:")
    for t in transactions[:5]:
        print(f"   - {t.post_date.strftime('%d/%m/%Y')}: £{t.amount:,.2f} | {t.customer_reference[:40]}")

    return transactions


def test_customer_loader():
    """Test the customer data loader"""
    print("\n" + "="*60)
    print("TEST 2: Customer Data Loader")
    print("="*60)

    if not CUSTOMER_REPORT_PATH.exists():
        print(f"❌ Customer file not found: {CUSTOMER_REPORT_PATH}")
        return None

    loader = CustomerLoader(CUSTOMER_REPORT_PATH)

    print(f"✅ Loaded {len(loader.customers)} customers")
    print(f"   Summary: {loader.get_summary()}")

    # Show sample customers
    print("\n   Sample customers:")
    for i, (code, customer) in enumerate(list(loader.customers.items())[:5]):
        print(f"   - {code}: {customer.get('name', 'N/A')}")

    return loader


def test_aka_loader():
    """Test the AKA pattern loader"""
    print("\n" + "="*60)
    print("TEST 3: AKA Pattern Loader")
    print("="*60)

    if not AKA_SHEET_PATH.exists():
        print(f"❌ AKA file not found: {AKA_SHEET_PATH}")
        return None

    loader = AKALoader(AKA_SHEET_PATH)

    print(f"✅ Loaded {len(loader.patterns)} AKA patterns")
    print(f"   Summary: {loader.get_summary()}")

    # Show sample patterns
    print("\n   Sample patterns:")
    for pattern in loader.patterns[:5]:
        print(f"   - '{pattern.pattern}' -> {pattern.customer_code}")

    return loader


def test_si_extraction():
    """Test SI invoice number extraction"""
    print("\n" + "="*60)
    print("TEST 4: SI Invoice Pattern Extraction")
    print("="*60)

    matcher = SIInvoiceMatcher()

    test_cases = [
        "SI-794931",
        "FTI CONSULTING LLPSI-794931 SC-2257859000217092559000N500000",
        "SI787264-SI788064",
        "2748699/SI-78696",
        "770909  771443  71",  # Should NOT match
        "BACS REMITTANCE PL",  # Should NOT match
    ]

    for test in test_cases:
        invoices = matcher.extract_invoice_numbers(test)
        status = "✅" if invoices else "❌"
        print(f"   {status} '{test[:50]}...' -> {invoices}")


def test_matching_pipeline(transactions, customer_loader, aka_loader):
    """Test the full matching pipeline"""
    print("\n" + "="*60)
    print("TEST 5: Full Matching Pipeline")
    print("="*60)

    if not transactions:
        print("❌ No transactions to test")
        return None

    orchestrator = MatchingOrchestrator(
        customer_loader=customer_loader,
        aka_loader=aka_loader
    )

    # Process transactions
    print(f"\n   Processing {len(transactions)} transactions...")
    matched = orchestrator.match_transactions(transactions)

    # Get stats
    stats = orchestrator.get_stats()

    print(f"\n   ✅ Matching Complete!")
    print(f"\n   Results:")
    print(f"   - Total processed: {stats['total_processed']}")
    print(f"   - Match rate: {stats.get('match_rate', 0):.1f}%")
    print(f"   - High confidence: {stats['high_confidence']} ({stats.get('high_confidence', 0)/max(stats['total_processed'],1)*100:.1f}%)")
    print(f"   - Medium confidence: {stats['medium_confidence']}")
    print(f"   - Low confidence: {stats['low_confidence']}")
    print(f"   - Unmatched: {stats['unmatched']}")

    print(f"\n   Layer breakdown:")
    print(f"   - Layer 1 (SI Invoice): {stats['layer1_matches']}")
    print(f"   - Layer 2 (AKA Pattern): {stats['layer2_matches']}")
    print(f"   - Layer 3 (Fuzzy Name): {stats['layer3_matches']}")
    print(f"   - Layer 4 (AI): {stats['layer4_matches']}")

    # Show sample matches
    print("\n   Sample HIGH confidence matches:")
    high_conf = [t for t in matched if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH]
    for t in high_conf[:5]:
        m = t.match_result
        print(f"   - £{t.amount:,.2f} -> {m.customer_code} ({m.customer_name[:30]}) via {m.match_method.value}")

    return matched


def test_excel_export(transactions):
    """Test Excel export generation"""
    print("\n" + "="*60)
    print("TEST 6: Excel Export Generation")
    print("="*60)

    if not transactions:
        print("❌ No transactions to export")
        return

    generator = ExcelGenerator(OUTPUT_DIR)

    # Generate Curtis review
    output_path = generator.generate_curtis_review(
        transactions,
        filename=f"TEST_Curtis_Review_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    )
    print(f"   ✅ Curtis review exported: {output_path}")

    # Generate Eagle import
    output_path = generator.generate_eagle_import(
        transactions,
        filename=f"TEST_Eagle_Import_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    )
    print(f"   ✅ Eagle import exported: {output_path}")


def run_all_tests():
    """Run all system tests"""
    print("\n" + "="*60)
    print("LIQUIDLINE BANK AUTOMATION - SYSTEM TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Test 1: Bank Parser
    transactions = test_bank_parser()

    # Test 2: Customer Loader
    customer_loader = test_customer_loader()

    # Test 3: AKA Loader
    aka_loader = test_aka_loader()

    # Test 4: SI Extraction
    test_si_extraction()

    # Test 5: Full Pipeline
    matched_transactions = test_matching_pipeline(transactions, customer_loader, aka_loader)

    # Test 6: Excel Export
    if matched_transactions:
        test_excel_export(matched_transactions)

    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)

    # Summary
    print("\n📊 Summary:")
    print(f"   - Bank parser: {'✅' if transactions else '❌'}")
    print(f"   - Customer loader: {'✅' if customer_loader else '❌'}")
    print(f"   - AKA loader: {'✅' if aka_loader else '❌'}")
    print(f"   - Matching pipeline: {'✅' if matched_transactions else '❌'}")


if __name__ == "__main__":
    run_all_tests()
