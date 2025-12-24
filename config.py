"""
Liquidline Bank Reconciliation Automation
Configuration Settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONTEXT_DIR = BASE_DIR / "context"
OUTPUT_DIR = BASE_DIR / "output"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Data Files
BANK_DATA_DIR = DATA_DIR
AKA_SHEET_PATH = DATA_DIR / "ALL HISTORY 2024-2025.xlsx"
CUSTOMER_REPORT_PATH = DATA_DIR / "customer report.xlsx"
CASH_BOOK_PATH = DATA_DIR / "Cash Book Reconciliation Main November 2025.xlsx"

# Matching Configuration
CONFIDENCE_THRESHOLDS = {
    "high": 0.85,      # GREEN - Auto-approve candidate
    "medium": 0.60,    # YELLOW - Review suggested match
    "low": 0.0         # RED - Exception queue
}

# Layer priorities (higher = tried first)
MATCHING_LAYERS = {
    "layer_1_si_invoice": {"priority": 1, "accuracy": 1.00},    # Exact SI-XXXXXX match
    "layer_2_aka_pattern": {"priority": 2, "accuracy": 0.95},   # AKA sheet lookup
    "layer_3_fuzzy_name": {"priority": 3, "accuracy": 0.85},    # Fuzzy customer name
    "layer_4_ai_inference": {"priority": 4, "accuracy": 0.70},  # Claude AI
}

# Bank CSV Column Mapping (Lloyds format)
BANK_CSV_COLUMNS = {
    "post_date": "Post Date",
    "account_number": "Account Number",
    "account_name": "Account Name",
    "type": "Type",
    "amount": "Amount",
    "customer_reference": "Customer Reference",
    "transaction_detail": "Transaction Detail",
    "balance": "Balance"
}

# Transaction types to process (skip Opening/Closing Ledger)
PROCESSABLE_TYPES = [
    "Bank Giro Credit",
    "Faster Payment",
    "CHAPS",
    "Direct Debit",
    "BACS"
]

# Exception types
EXCEPTION_CATEGORIES = [
    "vat_rounding",      # 1-2p VAT differences
    "niacs",             # NIACS card payments
    "vending",           # Vending cash operations
    "ifc",               # Inter-company charges
    "currency",          # Currency transactions
    "consolidated",      # Multiple invoices
    "group_one",         # BMW dealership group
    "tower_cco"          # Tower rental (CCO confirmation)
]

# SI Invoice pattern regex
SI_INVOICE_PATTERN = r'SI[-\s]?(\d{5,7})'

# Application settings
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
