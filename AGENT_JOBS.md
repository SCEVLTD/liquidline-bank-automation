# AGENT JOBS - Liquidline Bank Reconciliation

**Generated:** 2025-12-24 (Updated after Job 1 completion)
**Project:** Liquidline Bank Reconciliation Automation
**App URL:** https://liquidline.streamlit.app
**Repository:** https://github.com/SCEVLTD/liquidline-bank-automation

---

## JOB STATUS SUMMARY

| Job | Priority | Status | Type | Est. Time |
|-----|----------|--------|------|-----------|
| Job 1: Fix KPIs & Export | P0 | ✅ COMPLETE | Agent | - |
| Job 2: Configure Secrets | MANUAL | ⏳ Pending | User | 15 min |
| Job 3: Invoice-to-Customer Lookup | P1 | ⏳ Pending | Agent | 4-6 hrs |
| Job 4: Test Eagle Import | MANUAL | ⏳ Pending | User+Karen | 2-4 hrs |
| Job 5: Documentation & Video | P1 | ⏳ Pending | Agent | 4-8 hrs |
| Job 6: Pattern Learning | P2 | ⏳ Pending | Agent | 6-10 hrs |
| Job 7: Remittance Upload UI | P2 | ⏳ Pending | Agent | 3-5 hrs |

---

## ✅ JOB 1: Fix Matching KPIs & Export Logic - COMPLETE

**Status:** COMPLETED 2025-12-24

**Changes Made:**
- `src/matching/layer1_si.py` - SI matches without customer_code now MEDIUM
- `src/matching/orchestrator.py` - Added postable stats tracking
- `src/output/excel_generator.py` - Split exports into Ready to Post / Needs Review
- `src/output/eagle_bank_statement.py` - Fixed txn.date bug
- `app.py` - Added Postable Rate metric to UI

**Result:** App now shows honest "Postable Rate" alongside "Match Rate"

---

## JOB 2: Configure Streamlit Secrets (USER MANUAL ACTION)

**Type:** Manual user action (not agent task)
**Time:** 15 minutes
**Dependencies:** Streamlit Cloud account access

### Instructions for User

1. **Go to Streamlit Cloud Dashboard**
   - URL: https://share.streamlit.io
   - Sign in with your GitHub account

2. **Select the Liquidline App**
   - Click on "liquidline-bank-automation"
   - Click "Settings" (gear icon)

3. **Add Secrets**
   - Click "Secrets" tab
   - Paste the following configuration:

```toml
# ============================================
# LIQUIDLINE BANK AUTOMATION - SECRETS CONFIG
# ============================================

# AI MATCHING (Required for Layer 4)
# Get key from: https://openrouter.ai/keys
OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY-HERE"

# AUTHENTICATION
# Option 1: Simple password protection
APP_PASSWORD = "Liquidline2025!"

# Option 2: Email whitelist (uncomment to use instead of password)
# ALLOWED_EMAILS = "curtis@liquidline.co.uk,erin@liquidline.co.uk,karen@liquidline.co.uk"

# CLIENT BRANDING
CLIENT_NAME = "Liquidline"
PRIMARY_COLOR = "#1E88E5"
LOGO_URL = ""

# FEATURE FLAGS
FEATURE_AI_MATCHING = "true"
FEATURE_REMITTANCE = "true"
FEATURE_PATTERN_LEARNING = "false"
```

4. **Click "Save"**
   - App will automatically reboot
   - Test: Visit app URL, should show login prompt

### Verification Checklist
- [ ] Login prompt appears when accessing app
- [ ] Password "Liquidline2025!" works
- [ ] Layer 4 AI matching works (process a file, check for AI matches)
- [ ] Client branding shows "Liquidline" in header

---

## JOB 3: Implement Invoice-to-Customer Lookup (AGENT)

**Priority:** P1 (Should do before sign-off)
**Time:** 4-6 hours
**Type:** Code implementation

### Files to Create/Modify
- `src/data/invoice_loader.py` (NEW)
- `src/matching/layer1_si.py` (MODIFY)
- `app.py` (MODIFY - add invoice file upload)

### Robust Agent Prompt

```
You are implementing invoice-to-customer lookup for the Liquidline Bank Reconciliation system.

## CONTEXT

The system currently extracts SI invoice numbers (SI-780606) from bank transactions but doesn't know which customer they belong to. We need to load Eagle's invoice export to map invoices to customers.

**Current State:**
- Layer 1 (SI Invoice) finds invoice numbers in bank references
- But returns empty customer_code because there's no lookup
- These matches are now marked MEDIUM confidence (fixed in Job 1)
- Users must manually look up the customer in Eagle

**Target State:**
- User uploads Eagle invoice export (Excel/CSV)
- System builds invoice_number → customer_code lookup
- SI matches now resolve customer codes automatically
- Matches with customer codes become HIGH confidence + postable

## EXPECTED INVOICE DATA FORMAT

Eagle invoice export typically has these columns:
- Invoice Number: SI-XXXXXX
- Customer Code: 4036, 23111, LIQU001, etc.
- Customer Name: Company Ltd
- Invoice Amount: 1234.56
- Invoice Date: DD/MM/YYYY
- Status: Open, Paid, etc.

## IMPLEMENTATION STEPS

### Step 1: Create src/data/invoice_loader.py

```python
"""
Invoice data loader for Eagle invoice exports.
Maps invoice numbers to customer codes.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class InvoiceLoader:
    """
    Loads Eagle invoice export and builds lookup dictionary.
    """

    def __init__(self, file_path: Optional[str] = None):
        self.invoices: Dict[str, dict] = {}
        self.file_path = file_path

        if file_path:
            self.load(file_path)

    def load(self, file_path: str) -> int:
        """Load invoice data from Excel or CSV file."""
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Invoice file not found: {file_path}")
            return 0

        try:
            # Load file
            if path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)

            # Normalize column names
            df.columns = [str(c).lower().strip() for c in df.columns]

            # Find relevant columns (flexible matching)
            invoice_col = self._find_column(df, ['invoice number', 'invoice no', 'invoice', 'inv no', 'inv number'])
            customer_code_col = self._find_column(df, ['customer code', 'cust code', 'customer no', 'account code', 'account'])
            customer_name_col = self._find_column(df, ['customer name', 'cust name', 'name', 'company'])
            amount_col = self._find_column(df, ['amount', 'invoice amount', 'total', 'value'])

            if not invoice_col:
                logger.error("Could not find invoice number column")
                return 0

            # Build lookup
            for _, row in df.iterrows():
                invoice_num = self._normalize_invoice_number(str(row.get(invoice_col, '')))
                if not invoice_num:
                    continue

                self.invoices[invoice_num] = {
                    'invoice_number': invoice_num,
                    'customer_code': str(row.get(customer_code_col, '')).strip() if customer_code_col else '',
                    'customer_name': str(row.get(customer_name_col, '')).strip() if customer_name_col else '',
                    'amount': float(row.get(amount_col, 0)) if amount_col else 0.0
                }

            logger.info(f"Loaded {len(self.invoices)} invoices from {file_path}")
            return len(self.invoices)

        except Exception as e:
            logger.error(f"Error loading invoice file: {e}")
            return 0

    def _find_column(self, df: pd.DataFrame, names: list) -> Optional[str]:
        """Find column by checking multiple possible names."""
        for name in names:
            if name in df.columns:
                return name
            # Partial match
            for col in df.columns:
                if name in col:
                    return col
        return None

    def _normalize_invoice_number(self, invoice: str) -> str:
        """Normalize SI invoice number format."""
        invoice = invoice.upper().strip()

        # Extract SI number
        match = re.search(r'SI[-\s]?(\d{5,7})', invoice)
        if match:
            return f"SI-{match.group(1)}"

        # Handle S1 typo
        match = re.search(r'S1[-\s]?(\d{5,7})', invoice)
        if match:
            return f"SI-{match.group(1)}"

        return invoice if invoice.startswith('SI') else ''

    def lookup(self, invoice_number: str) -> Optional[dict]:
        """Look up customer info by invoice number."""
        normalized = self._normalize_invoice_number(invoice_number)
        return self.invoices.get(normalized)

    def get_customer_code(self, invoice_number: str) -> str:
        """Get customer code for an invoice."""
        info = self.lookup(invoice_number)
        return info.get('customer_code', '') if info else ''

    def get_stats(self) -> dict:
        """Get loader statistics."""
        return {
            'total_invoices': len(self.invoices),
            'with_customer_code': sum(1 for i in self.invoices.values() if i.get('customer_code')),
            'source_file': str(self.file_path) if self.file_path else None
        }
```

### Step 2: Modify src/matching/layer1_si.py

In the `__init__` method, accept an invoice_loader parameter:

```python
def __init__(self, invoice_lookup_func=None, customer_lookup_func=None, invoice_loader=None):
    self.invoice_lookup = invoice_lookup_func
    self.customer_lookup = customer_lookup_func
    self.invoice_loader = invoice_loader  # NEW
    self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SI_PATTERNS]
```

In `_create_basic_match`, try to resolve customer via invoice_loader:

```python
def _create_basic_match(self, transaction: Transaction, invoices: List[str]) -> MatchResult:
    """Create basic match when we have invoices but no lookup"""

    # TRY TO RESOLVE CUSTOMER VIA INVOICE LOADER
    customer_code = ""
    customer_name = ""

    if self.invoice_loader:
        for invoice_num in invoices:
            info = self.invoice_loader.lookup(invoice_num)
            if info and info.get('customer_code'):
                customer_code = info['customer_code']
                customer_name = info.get('customer_name', '')
                break

    # Create allocations
    allocations = []
    for invoice_num in invoices:
        allocation = InvoiceAllocation(
            invoice_number=invoice_num,
            invoice_amount=0,
            allocated_amount=transaction.amount / len(invoices) if invoices else 0,
        )
        allocations.append(allocation)

    # Set confidence based on whether we resolved customer
    if customer_code:
        # Have customer code = HIGH confidence, postable
        return MatchResult(
            customer_code=customer_code,
            customer_name=customer_name,
            confidence_score=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            match_method=MatchMethod.LAYER_1_SI_INVOICE,
            invoice_allocations=allocations,
            match_details=f"SI invoice matched to customer {customer_code}: {', '.join(invoices)}"
        )
    else:
        # No customer code = MEDIUM confidence, needs lookup
        return MatchResult(
            customer_code="",
            customer_name="",
            confidence_score=0.70,
            confidence_level=ConfidenceLevel.MEDIUM,
            match_method=MatchMethod.LAYER_1_SI_INVOICE,
            invoice_allocations=allocations,
            match_details=f"SI invoice pattern found: {', '.join(invoices)} (NEEDS CUSTOMER LOOKUP - not postable)"
        )
```

### Step 3: Modify app.py - Add Invoice Upload

In the sidebar, after AKA patterns loading, add:

```python
# Invoice data upload (optional)
st.subheader("📋 Invoice Data (Optional)")
invoice_file = st.file_uploader(
    "Upload Eagle invoice export",
    type=['xlsx', 'xls', 'csv'],
    help="Optional: Upload invoice export to enable SI-to-customer lookup"
)

if invoice_file:
    # Save temporarily
    temp_path = DATA_DIR / f"invoices_{invoice_file.name}"
    with open(temp_path, 'wb') as f:
        f.write(invoice_file.getvalue())

    try:
        from src.data.invoice_loader import InvoiceLoader
        invoice_loader = InvoiceLoader(str(temp_path))
        st.success(f"✅ Loaded {len(invoice_loader.invoices)} invoices")

        # Pass to orchestrator
        if st.session_state.orchestrator:
            st.session_state.orchestrator.layer1.invoice_loader = invoice_loader
    except Exception as e:
        st.warning(f"⚠️ Could not load invoices: {e}")
```

## TESTING

After implementation:

1. Create test invoice file with sample data
2. Run test_system.py
3. Verify SI matches now have customer codes
4. Check postable_rate improves
5. Deploy to Streamlit Cloud
6. Test invoice upload in live app

## ACCEPTANCE CRITERIA

- [ ] InvoiceLoader class created and working
- [ ] Layer 1 uses invoice lookup when available
- [ ] Invoice file upload in Streamlit sidebar
- [ ] SI matches with customer codes are HIGH confidence
- [ ] SI matches without customer codes remain MEDIUM
- [ ] test_system.py passes
- [ ] No regressions in existing functionality
```

---

## JOB 4: Test Eagle Import Format (USER MANUAL + KAREN)

**Type:** Manual user action requiring client access
**Time:** 2-4 hours
**Dependencies:** Eagle dev site access from Karen

### Instructions

1. **Get Eagle Access**
   - Contact Karen to request dev site access
   - Karen to set up supplier login for SM

2. **Export Test File**
   - Run the app, process a bank file
   - Click "Export Eagle Import"
   - Download the Excel file

3. **Import to Eagle**
   - Log into Eagle dev environment
   - Navigate to: Bank Reconciliation → Import
   - Upload the test file
   - Document any errors

4. **Fix Format Issues (if any)**
   - Work with agent to adjust `src/output/eagle_bank_statement.py`
   - Re-test until successful

5. **Document Success**
   - Take screenshot of successful import
   - Verify transactions appear in correct customer accounts
   - Update PROGRESS.md with results

### Expected Eagle Format
Based on Bank Reconciliation Settings screen:
- Column A: Date (DD/MM/YYYY)
- Column B: Type (BGC, FP, etc.)
- Column C: Reference
- Column D: Received (credits)
- Column E: Paid (debits)
- Column F: Balance (optional)

---

## JOB 5: Create Documentation & Video (AGENT)

**Priority:** P1
**Time:** 4-8 hours
**Type:** Documentation creation

### Files to Create
- `docs/QUICK_START_GUIDE.md` (EXPAND existing)
- `docs/USER_MANUAL.md` (NEW)
- Tutorial video script

### Robust Agent Prompt

```
You are creating user documentation for the Liquidline Bank Reconciliation system.

## CONTEXT

**Project:** Liquidline Bank Reconciliation Automation
**Users:** Non-technical finance team (Curtis, Erin, Karen)
**App URL:** https://liquidline.streamlit.app
**Company:** Liquidline Limited (£50M coffee/vending)
**Contract:** £10,000 fixed price project

## AUDIENCE PROFILE

**Curtis (Cash Posting)**
- Daily task: Post bank receipts to customer accounts in Eagle
- Currently: Manual matching in spreadsheets
- Need: Quick approval of high-confidence matches
- Skill level: Excel proficient, not technical

**Erin (Bank Reconciliation)**
- Weekly task: Reconcile bank statement to Eagle ledger
- Currently: Manual comparison in spreadsheets
- Need: Clear summary of what's matched vs pending
- Skill level: Excel proficient, not technical

**Karen (Finance Director)**
- Oversight: Ensure accuracy of cash posting
- Concern: Two-step Eagle process (receipt → allocation)
- Need: Audit trail and exception reporting
- Skill level: Eagle expert, understands process

## DOCUMENTATION TO CREATE

### 1. docs/QUICK_START_GUIDE.md (Expand existing)

Current guide is minimal. Expand to include:

```markdown
# Liquidline Bank Reconciliation - Quick Start Guide

## Welcome

This system automates 70-80% of your daily cash posting and bank reconciliation work.

## Getting Started

### Step 1: Access the App

1. Open your browser (Chrome recommended)
2. Go to: https://liquidline.streamlit.app
3. Enter password: [provided by administrator]
4. You should see the main dashboard

[SCREENSHOT: Login screen]

### Step 2: Load Reference Data

Before processing bank files, load the reference data:

1. In the left sidebar, click **"Load Reference Data"**
2. Wait for confirmation:
   - ✅ Loaded 16,102 customers
   - ✅ Loaded 547 AKA patterns

[SCREENSHOT: Reference data loaded]

### Step 3: Process a Bank File

1. Under "Select existing bank file", choose today's bank download
2. Click **"🚀 Process Transactions"**
3. Wait for matching to complete (usually 10-30 seconds)

[SCREENSHOT: Processing results]

### Step 4: Review Results

Results are color-coded:
- 🟢 **GREEN (High Confidence)** - Ready to post, no review needed
- 🟡 **YELLOW (Medium Confidence)** - Check the match before posting
- 🔴 **RED (Low/Exception)** - Manual lookup required

### Step 5: Export for Eagle

Click one of:
- **Export Curtis Review** - Full spreadsheet with all columns
- **Export Eagle Import** - Just the postable rows for Eagle import

## For Curtis: Daily Cash Posting

1. Click **"Curtis Cash Posting"** in sidebar
2. Review the **Ready for Approval** section (green rows)
3. Click **"Approve All High Confidence"** to batch approve
4. Review yellow rows one by one
5. Export to Eagle when done

## For Erin: Bank Reconciliation

1. Click **"Erin Reconciliation"** in sidebar
2. Check the **Summary** tab for overview
3. Review **Items Needing Attention** tab
4. Once all items resolved, totals should match

## Troubleshooting

### "No transactions processed"
- Make sure you clicked "Load Reference Data" first
- Check the file is a valid Lloyds CSV

### "Low match rate"
- Check the bank file date - is customer data current?
- Contact support if consistently below 80%

### "Can't login"
- Check password is correct (case sensitive)
- Try refreshing the page
- Clear browser cache if issues persist

## Support

For help, contact: [support email]
```

### 2. docs/USER_MANUAL.md (New comprehensive guide)

Create detailed manual covering:

```markdown
# Liquidline Bank Reconciliation - User Manual

## Table of Contents
1. Introduction
2. System Overview
3. Curtis Workflow (Cash Posting)
4. Erin Workflow (Bank Reconciliation)
5. Understanding Match Results
6. Export Formats
7. Troubleshooting
8. Glossary

## 1. Introduction

### What This System Does
[Explain the automation in business terms]

### Who Should Use This
[Curtis, Erin, Karen - their roles]

## 2. System Overview

### The Matching Engine
The system uses a 5-layer matching approach:

| Layer | Method | Accuracy | Example |
|-------|--------|----------|---------|
| Layer 0 | Remittance Match | ~100% | PDF remittance with exact invoices |
| Layer 1 | SI Invoice Pattern | ~100% | "SI-780606" in bank reference |
| Layer 2 | AKA Sheet Lookup | ~95% | Known patterns like "TOYOTA LEICESTER" |
| Layer 3 | Fuzzy Name Match | ~85% | "FTI CONSULTING" → FTI Consulting LLP |
| Layer 4 | AI Inference | ~70% | Ambiguous names resolved by AI |

### Confidence Levels
[Explain GREEN/YELLOW/RED]

### Postable vs Matched
[Explain that postable requires customer code]

## 3. Curtis Workflow

### Daily Process
[Step by step with screenshots]

### One-Click Approval
[Explain batch approval]

### Manual Lookups
[What to do for yellow/red items]

## 4. Erin Workflow

### Weekly Reconciliation
[Step by step]

### Summary View
[Explain the metrics]

### Items Needing Attention
[How to resolve]

## 5. Understanding Match Results

### Reading the Results Table
[Column by column explanation]

### Why Some Items Need Review
[Common reasons]

## 6. Export Formats

### Curtis Review Export
[Columns and how to use]

### Eagle Import Export
[Format and import process]

### All Data Export
[Raw data for analysis]

## 7. Troubleshooting

### Common Issues
[FAQ format]

### Error Messages
[What they mean and how to fix]

## 8. Glossary

- **AKA Pattern**: Known alias for a customer
- **Customer Code**: Eagle account number
- **SI Invoice**: Sales Invoice number format
- **Postable**: Has customer code, ready for Eagle
- **Match Rate**: Percentage with any match
- **Postable Rate**: Percentage ready for Eagle import
```

### 3. Video Script (for recording)

Create a script for a 5-10 minute walkthrough video:

```markdown
# Video Walkthrough Script

## Duration: 5-7 minutes

### Intro (30 seconds)
"Welcome to the Liquidline Bank Reconciliation system. This video will show you how to process your daily bank download and export results for Eagle."

### Demo Flow

1. **Login** (30 seconds)
   - Show app URL
   - Enter password
   - Show main dashboard

2. **Load Data** (30 seconds)
   - Click Load Reference Data
   - Show success messages
   - Explain what's loaded

3. **Process Bank File** (1 minute)
   - Select bank file from dropdown
   - Click Process
   - Show results loading
   - Explain the metrics (Match Rate vs Postable Rate)

4. **Review Results** (2 minutes)
   - Show High Confidence tab (green)
   - Show Medium tab (yellow)
   - Show Exception tab (red)
   - Explain what each means

5. **Curtis Cash Posting Page** (1 minute)
   - Navigate to Curtis page
   - Show ready for approval section
   - Demo one-click approval
   - Show export button

6. **Erin Reconciliation Page** (1 minute)
   - Navigate to Erin page
   - Show summary stats
   - Show items needing attention
   - Explain reconciliation process

7. **Export to Eagle** (30 seconds)
   - Click Export Eagle Import
   - Show downloaded file
   - Explain Ready to Post vs Needs Review sheets

8. **Wrap Up** (30 seconds)
   - Summary of daily workflow
   - Where to get help
   - Contact info
```

## ACCEPTANCE CRITERIA

- [ ] Quick Start Guide has screenshots and step-by-step instructions
- [ ] User Manual covers all user workflows
- [ ] Language is non-technical, suitable for finance users
- [ ] All screenshots have [SCREENSHOT: description] placeholders
- [ ] Video script is clear and covers complete workflow
- [ ] Documents are in docs/ folder
- [ ] No jargon - explain technical terms
```

---

## JOB 6: Implement Pattern Learning (AGENT)

**Priority:** P2 (Enhancement)
**Time:** 6-10 hours
**Type:** Code implementation

### Files to Create/Modify
- `src/data/pattern_store.py` (NEW)
- `pages/1_Curtis_Cash_Posting.py` (MODIFY)
- `app.py` (MODIFY)

### Robust Agent Prompt

```
You are implementing pattern learning for the Liquidline Bank Reconciliation system.

## CONTEXT

**Requirement:** When Curtis confirms a match (e.g., "KIRLY PROPERTY" → customer 9500), the system should learn this pattern for future use.

**Current State:**
- AKA patterns loaded from Excel file (547 patterns)
- No way to add new patterns from the UI
- Curtis manually notes new patterns for later

**Target State:**
- "Add to Patterns" button next to each match
- Patterns saved to JSON file
- Loaded on startup alongside AKA patterns
- Persists between sessions

## IMPLEMENTATION

### Step 1: Create src/data/pattern_store.py

```python
"""
Pattern Store - Manages learned customer patterns.
Persists patterns to JSON file for reuse.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PatternStore:
    """
    Stores and manages learned customer patterns.
    Patterns are saved as JSON for persistence.
    """

    DEFAULT_PATH = "data/learned_patterns.json"

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path or self.DEFAULT_PATH)
        self.patterns: Dict[str, dict] = {}
        self.load_patterns()

    def load_patterns(self) -> int:
        """Load patterns from JSON file."""
        if not self.file_path.exists():
            logger.info(f"Pattern file not found, starting fresh: {self.file_path}")
            return 0

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.patterns = data.get('patterns', {})
            logger.info(f"Loaded {len(self.patterns)} learned patterns")
            return len(self.patterns)
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            return 0

    def save_patterns(self) -> bool:
        """Save patterns to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'version': '1.0',
                'updated': datetime.now().isoformat(),
                'count': len(self.patterns),
                'patterns': self.patterns
            }

            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.patterns)} patterns to {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")
            return False

    def add_pattern(
        self,
        bank_reference: str,
        customer_code: str,
        customer_name: str = "",
        source: str = "learned"
    ) -> bool:
        """
        Add a new pattern.

        Args:
            bank_reference: The bank text to match (e.g., "KIRLY PROPERTY")
            customer_code: Eagle customer code (e.g., "9500")
            customer_name: Customer name for reference
            source: Where pattern came from (learned, manual, etc.)
        """
        # Normalize the reference
        normalized = bank_reference.upper().strip()

        if not normalized or not customer_code:
            return False

        # Don't duplicate
        if normalized in self.patterns:
            logger.info(f"Pattern already exists: {normalized}")
            return False

        self.patterns[normalized] = {
            'bank_reference': normalized,
            'customer_code': str(customer_code).strip(),
            'customer_name': customer_name,
            'source': source,
            'created': datetime.now().isoformat()
        }

        # Auto-save
        self.save_patterns()
        logger.info(f"Added pattern: {normalized} -> {customer_code}")
        return True

    def remove_pattern(self, bank_reference: str) -> bool:
        """Remove a pattern."""
        normalized = bank_reference.upper().strip()
        if normalized in self.patterns:
            del self.patterns[normalized]
            self.save_patterns()
            return True
        return False

    def lookup(self, text: str) -> Optional[dict]:
        """Look up a pattern by bank reference text."""
        normalized = text.upper().strip()

        # Exact match
        if normalized in self.patterns:
            return self.patterns[normalized]

        # Partial match (if bank text contains the pattern)
        for pattern, info in self.patterns.items():
            if pattern in normalized:
                return info

        return None

    def get_customer_code(self, text: str) -> str:
        """Get customer code for text, or empty string if not found."""
        match = self.lookup(text)
        return match.get('customer_code', '') if match else ''

    def get_all_patterns(self) -> List[dict]:
        """Get all patterns as a list."""
        return list(self.patterns.values())

    def get_stats(self) -> dict:
        """Get pattern store statistics."""
        return {
            'total_patterns': len(self.patterns),
            'sources': {
                source: sum(1 for p in self.patterns.values() if p.get('source') == source)
                for source in set(p.get('source', 'unknown') for p in self.patterns.values())
            },
            'file_path': str(self.file_path)
        }
```

### Step 2: Integrate with AKA Loader

In `src/data/aka_loader.py`, add method to accept learned patterns:

```python
def add_learned_patterns(self, pattern_store: 'PatternStore'):
    """Add learned patterns to the AKA lookup."""
    for pattern_info in pattern_store.get_all_patterns():
        self.patterns[pattern_info['bank_reference']] = {
            'code': pattern_info['customer_code'],
            'name': pattern_info.get('customer_name', ''),
            'source': 'learned'
        }
```

### Step 3: Add to Curtis Cash Posting page

In `pages/1_Curtis_Cash_Posting.py`, add "Add to Patterns" button:

```python
# In the transaction display loop
for idx, txn in enumerate(transactions):
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        st.write(f"£{txn.amount:,.2f}")
        st.caption(txn.customer_reference[:40])

    with col2:
        if txn.match_result:
            st.write(f"{txn.match_result.customer_code} - {txn.match_result.customer_name}")

    with col3:
        # Show confidence
        level = txn.match_result.confidence_level.value if txn.match_result else "none"
        st.write(level.upper())

    with col4:
        # Add to Patterns button
        if txn.match_result and txn.match_result.customer_code:
            if st.button("📌 Save Pattern", key=f"pattern_{idx}"):
                from src.data.pattern_store import PatternStore
                store = PatternStore()
                success = store.add_pattern(
                    bank_reference=txn.customer_reference or txn.transaction_detail,
                    customer_code=txn.match_result.customer_code,
                    customer_name=txn.match_result.customer_name
                )
                if success:
                    st.success("Pattern saved!")
                else:
                    st.info("Pattern already exists")
```

### Step 4: Load patterns on startup in app.py

```python
# In load_reference_data() function, after loading AKA:

# Load learned patterns
from src.data.pattern_store import PatternStore
pattern_store = PatternStore()
learned_count = len(pattern_store.patterns)

if learned_count > 0:
    # Add to AKA loader
    if aka_loader:
        aka_loader.add_learned_patterns(pattern_store)
        st.success(f"✅ Added {learned_count} learned patterns")

st.session_state.pattern_store = pattern_store
```

## TESTING

1. Process a bank file
2. Find a transaction, note the bank reference and customer
3. Click "Add to Patterns"
4. Check data/learned_patterns.json is created
5. Restart app, verify pattern count includes learned patterns
6. Process same bank file - should now match without AI

## ACCEPTANCE CRITERIA

- [ ] PatternStore class created
- [ ] Patterns persist to JSON file
- [ ] "Add to Patterns" button in Curtis page
- [ ] Learned patterns loaded on startup
- [ ] Integrated with AKA loader
- [ ] No regressions in existing matching
```

---

## JOB 7: Add Remittance Upload UI (AGENT)

**Priority:** P2 (Enhancement)
**Time:** 3-5 hours
**Type:** Code implementation

### Files to Modify
- `app.py` (MODIFY)
- `src/matching/layer0_remittance.py` (MODIFY if needed)

### Robust Agent Prompt

```
You are adding remittance upload functionality to the Liquidline Bank Reconciliation app.

## CONTEXT

**Current State:**
- Remittance PDFs must be manually placed in `remittance_examples/` folder
- System parses PDFs using RemittanceParser
- Layer 0 matches bank transactions against parsed remittances by amount

**Target State:**
- Users can drag-drop remittance PDFs in the Streamlit UI
- PDFs parsed immediately on upload
- Stored in session state for matching
- No folder management required

## IMPLEMENTATION

### Step 1: Add Remittance Upload Section to app.py sidebar

In `render_sidebar()` function, add before "Reference Data" section:

```python
def render_sidebar():
    """Render sidebar with data loading and stats"""
    with st.sidebar:
        st.title(f"💰 {client_config['client_name']}")
        st.subheader("Bank Reconciliation Automation")

        st.divider()

        # ===== REMITTANCE UPLOAD SECTION (NEW) =====
        st.subheader("📄 Remittance Advices")
        st.caption("Upload remittance PDFs for high-accuracy matching")

        uploaded_remittances = st.file_uploader(
            "Upload remittance PDFs",
            type=['pdf'],
            accept_multiple_files=True,
            help="Drag and drop remittance advice PDFs. These will be matched first (highest priority)."
        )

        if uploaded_remittances:
            process_remittance_uploads(uploaded_remittances)

        # Show remittance stats if any loaded
        if 'parsed_remittances' in st.session_state and st.session_state.parsed_remittances:
            count = len(st.session_state.parsed_remittances)
            total = sum(r.total_amount for r, _ in st.session_state.parsed_remittances)
            st.success(f"✅ {count} remittances (£{total:,.2f})")

        st.divider()

        # Rest of sidebar...
```

### Step 2: Create helper function to process uploads

```python
def process_remittance_uploads(uploaded_files):
    """Process uploaded remittance PDF files."""
    from src.matching.remittance_parser import RemittanceParser

    parser = RemittanceParser()

    # Initialize session state if needed
    if 'parsed_remittances' not in st.session_state:
        st.session_state.parsed_remittances = []

    new_count = 0

    for uploaded_file in uploaded_files:
        # Check if already processed (by filename)
        existing_names = [source for _, source in st.session_state.parsed_remittances]
        if uploaded_file.name in existing_names:
            continue

        try:
            # Save temporarily
            temp_path = DATA_DIR / f"temp_{uploaded_file.name}"
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getvalue())

            # Parse the PDF
            remittance = parser.parse_pdf(str(temp_path))

            if remittance.total_amount > 0:
                st.session_state.parsed_remittances.append((remittance, uploaded_file.name))
                new_count += 1
                logger.info(f"Parsed remittance: {uploaded_file.name} -> £{remittance.total_amount}")

            # Clean up temp file
            temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.warning(f"Could not parse {uploaded_file.name}: {e}")
            logger.error(f"Remittance parse error: {e}")

    if new_count > 0:
        st.success(f"Processed {new_count} new remittance(s)")

        # Update orchestrator if initialized
        if st.session_state.orchestrator:
            # Add parsed remittances to Layer 0
            for remittance, source in st.session_state.parsed_remittances:
                st.session_state.orchestrator.layer0.parsed_remittances.append((remittance, source))
```

### Step 3: Clear remittances option

Add a button to clear uploaded remittances:

```python
# In the remittance section
if 'parsed_remittances' in st.session_state and st.session_state.parsed_remittances:
    col1, col2 = st.columns(2)
    with col1:
        count = len(st.session_state.parsed_remittances)
        st.metric("Loaded", count)
    with col2:
        if st.button("🗑️ Clear", help="Clear all uploaded remittances"):
            st.session_state.parsed_remittances = []
            if st.session_state.orchestrator:
                st.session_state.orchestrator.layer0.parsed_remittances = []
            st.rerun()
```

### Step 4: Show remittance details expandable

```python
# Show details of loaded remittances
if st.session_state.parsed_remittances:
    with st.expander("View uploaded remittances"):
        for remittance, source in st.session_state.parsed_remittances:
            st.write(f"**{source}**")
            st.write(f"- Customer: {remittance.customer_name}")
            st.write(f"- Amount: £{remittance.total_amount:,.2f}")
            st.write(f"- Invoices: {', '.join([inv.invoice_number for inv in remittance.invoices])}")
            st.divider()
```

### Step 5: Ensure orchestrator uses uploaded remittances

In `process_bank_file()` function, before processing:

```python
def process_bank_file(file_path: Path):
    """Process a bank file through the matching engine"""
    if not st.session_state.data_loaded:
        st.error("Please load reference data first")
        return

    with st.spinner(f"Processing {file_path.name}..."):
        try:
            # Ensure remittances are loaded into orchestrator
            if 'parsed_remittances' in st.session_state:
                st.session_state.orchestrator.layer0.parsed_remittances = st.session_state.parsed_remittances

            # Parse bank file
            parser = BankParser()
            transactions = parser.parse_file(file_path)
            # ... rest of function
```

## TESTING

1. Start the app
2. Upload sample remittances from `remittance_examples/` folder
3. Verify they show in sidebar with totals
4. Process a bank file
5. Check that remittance matches appear (Layer 0)
6. Clear remittances, re-process, verify no Layer 0 matches

## ACCEPTANCE CRITERIA

- [ ] File uploader for PDFs in sidebar
- [ ] Multi-file upload supported
- [ ] Remittances parsed immediately
- [ ] Stats shown (count, total amount)
- [ ] Expandable details view
- [ ] Clear button works
- [ ] Layer 0 uses uploaded remittances for matching
- [ ] No regressions in existing functionality
```

---

## EXECUTION ORDER

### Phase 1: Critical (Before Demo)
1. ~~**Job 1** - Fix KPIs & Export Logic~~ ✅ COMPLETE
2. **Job 2** - Configure Streamlit Secrets (USER MANUAL)

### Phase 2: High Priority (Before Sign-off)
3. **Job 3** - Invoice-to-Customer Lookup (AGENT)
4. **Job 4** - Test Eagle Import (USER MANUAL + Karen)

### Phase 3: Documentation (Before Training)
5. **Job 5** - Create Documentation & Video (AGENT)

### Phase 4: Enhancements (Post-Delivery)
6. **Job 6** - Pattern Learning (AGENT)
7. **Job 7** - Remittance Upload UI (AGENT)

---

## SUCCESS CRITERIA

After all jobs complete:

- [ ] ✅ "Postable rate" shown in UI (Job 1 - DONE)
- [ ] Export only includes rows with customer codes (Job 1 - DONE)
- [ ] SI-only matches without codes marked MEDIUM (Job 1 - DONE)
- [ ] Login required to access app (Job 2)
- [ ] Layer 4 AI working (Job 2)
- [ ] SI matches resolve customer codes from invoice data (Job 3)
- [ ] Eagle import tested successfully (Job 4)
- [ ] Quick Start Guide complete with screenshots (Job 5)
- [ ] User Manual covers all workflows (Job 5)
- [ ] Video walkthrough recorded (Job 5)
- [ ] Pattern learning saves new patterns (Job 6)
- [ ] Remittance PDFs uploadable via UI (Job 7)
