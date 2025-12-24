# AGENT JOBS - Liquidline Fix Plan

Generated: 2025-12-24
Based on: AUDIT_REPORT.md + docs/AUDIT_REPORT_2025-12-24.md

---

## JOB 1: Fix Matching KPIs & Export Logic (P0 - CRITICAL)
**Estimated Time:** 2-4 hours
**Files to Modify:**
- `src/matching/layer1_si.py`
- `src/matching/orchestrator.py`
- `src/output/excel_generator.py`
- `src/output/eagle_bank_statement.py`
- `app.py`

**Tasks:**
1. Change SI invoice matcher to set confidence to MEDIUM (not HIGH) when customer_code is empty
2. Add "postable" flag to MatchResult model: `postable = bool(customer_code)`
3. Update orchestrator stats to report:
   - "Match rate (any match)"
   - "Postable rate (customer code present)"
   - "High-confidence postable rate"
4. Fix bug in eagle_bank_statement.py: change `txn.date` to `txn.post_date`
5. Update Excel export to:
   - Only include rows with customer_code in "Ready to Post" sheet
   - Move rows without customer_code to "Needs Review" sheet
6. Update app.py UI to show both metrics clearly

**Acceptance Criteria:**
- SI-only matches without customer code show as MEDIUM, not HIGH
- Export only includes postable rows in primary sheet
- UI shows honest "postable rate" metric
- No `AttributeError` on txn.date

**Prompt for Agent:**
```
You are fixing critical issues in the Liquidline Bank Reconciliation system.

PROBLEM: The system reports 100% match rate, but 27% of exported rows have missing customer codes. This is misleading because those rows cannot be posted to Eagle without manual work.

FILES TO REVIEW:
- src/matching/layer1_si.py (SI invoice matcher)
- src/matching/orchestrator.py (stats calculation)
- src/output/excel_generator.py (Excel export)
- src/output/eagle_bank_statement.py (has bug: txn.date should be txn.post_date)
- app.py (UI display)

TASKS:
1. In layer1_si.py: When customer_code is empty, set confidence to MEDIUM not HIGH
2. In orchestrator.py: Add separate stats for "postable" (has customer_code) vs "matched" (any match)
3. In eagle_bank_statement.py: Fix bug - change txn.date to txn.post_date
4. In excel_generator.py: Split export into "Ready to Post" (has customer code) and "Needs Review" (missing code)
5. In app.py: Update UI to show "Postable Rate" alongside "Match Rate"

DO NOT break existing functionality. Run test_system.py after changes to verify.
```

---

## JOB 2: Configure Streamlit Secrets (MANUAL - User Must Do)
**Estimated Time:** 15 minutes
**Files:** None (Streamlit Cloud dashboard)

**Tasks:**
1. Go to https://share.streamlit.io → Sign in
2. Click on liquidline app → Settings → Secrets
3. Add the following:

```toml
# AI MATCHING
OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY-HERE"

# SECURITY
APP_PASSWORD = "Liquidline2025!"

# CLIENT BRANDING
CLIENT_NAME = "Liquidline"
PRIMARY_COLOR = "#1E88E5"

# FEATURES
FEATURE_AI_MATCHING = "true"
FEATURE_REMITTANCE = "true"
```

4. Click Save
5. Verify app reboots and shows login prompt

**Acceptance Criteria:**
- Layer 4 AI matching works (test with ambiguous transaction)
- Login prompt appears when accessing app
- Client branding shows "Liquidline"

---

## JOB 3: Implement Invoice-to-Customer Lookup (P1)
**Estimated Time:** 4-6 hours
**Files to Create/Modify:**
- `src/data/invoice_loader.py` (NEW)
- `src/matching/layer1_si.py` (MODIFY)
- `app.py` (MODIFY - add invoice file upload)

**Tasks:**
1. Create InvoiceLoader class to load Eagle invoice export
2. Build invoice_number → customer_code lookup dictionary
3. Wire lookup into SIInvoiceMatcher
4. Add invoice file upload to Streamlit sidebar
5. When SI invoice found, lookup customer code from invoice data

**Prompt for Agent:**
```
You are implementing invoice-to-customer lookup for the Liquidline system.

PROBLEM: SI invoice numbers (SI-780606) are extracted from bank transactions but we don't know which customer they belong to. We need to load Eagle's invoice export to map invoices to customers.

EXPECTED INVOICE DATA FORMAT:
- Column: Invoice Number (SI-XXXXXX)
- Column: Customer Code (4036, 23111, etc)
- Column: Customer Name
- Column: Amount

TASKS:
1. Create src/data/invoice_loader.py with InvoiceLoader class
2. Load Excel/CSV export from Eagle with invoice data
3. Build lookup: invoice_number → customer_code
4. Modify src/matching/layer1_si.py to use this lookup
5. Add invoice file upload to sidebar in app.py
6. When SI invoice found, resolve customer code from lookup

Test with sample data and verify SI matches now have customer codes.
```

---

## JOB 4: Test Eagle Import Format (MANUAL - Needs Client Access)
**Estimated Time:** 2-4 hours
**Dependencies:** Need Eagle dev site access from Karen

**Tasks:**
1. Export test file from app (Eagle Import format)
2. Log into Eagle dev environment
3. Navigate to Bank Reconciliation → Import
4. Upload test file
5. Document any errors
6. Fix format issues if found
7. Re-test until successful

**Acceptance Criteria:**
- Eagle accepts import without errors
- Transactions appear in correct customer accounts
- Screenshot evidence of successful import

---

## JOB 5: Create Documentation & Video (P1)
**Estimated Time:** 4-8 hours
**Files to Create:**
- `docs/QUICK_START_GUIDE.md` (EXPAND)
- `docs/USER_MANUAL.md` (NEW)
- `assets/tutorial_video.mp4` (NEW)

**Tasks:**
1. Expand Quick Start Guide with screenshots
2. Create comprehensive User Manual covering:
   - Loading reference data
   - Processing bank files
   - Understanding confidence levels
   - Curtis workflow (one-click approval)
   - Erin workflow (reconciliation check)
   - Exporting for Eagle
3. Record 5-10 minute video walkthrough

**Prompt for Agent:**
```
You are creating documentation for the Liquidline Bank Reconciliation system.

AUDIENCE: Non-technical finance users (Curtis, Erin, Karen)

CREATE:
1. docs/QUICK_START_GUIDE.md with:
   - Step-by-step instructions with screenshots
   - Common problems and solutions
   - Contact info for support

2. docs/USER_MANUAL.md with:
   - Full system overview
   - Detailed workflow for Curtis (cash posting)
   - Detailed workflow for Erin (reconciliation)
   - Export formats explained
   - Troubleshooting guide

Use clear, simple language. Avoid technical jargon.
Include placeholder markers for screenshots: [SCREENSHOT: description]
```

---

## JOB 6: Implement Pattern Learning (P2)
**Estimated Time:** 6-10 hours
**Files to Create/Modify:**
- `src/data/pattern_store.py` (NEW)
- `pages/1_Curtis_Cash_Posting.py` (MODIFY)
- `app.py` (MODIFY)

**Tasks:**
1. Create PatternStore class (JSON/CSV persistence)
2. Add "Add to Patterns" button in Curtis Cash Posting page
3. When user confirms a match, save pattern to store
4. Load custom patterns on startup
5. Integrate with AKA loader

**Prompt for Agent:**
```
You are implementing pattern learning for the Liquidline system.

REQUIREMENT: When Curtis confirms a match (e.g., "KIRLY PROPERTY" → customer 9500), the system should learn this pattern for future use.

IMPLEMENTATION:
1. Create src/data/pattern_store.py:
   - PatternStore class
   - Methods: add_pattern(), load_patterns(), save_patterns()
   - Store as JSON file in data/learned_patterns.json

2. Modify pages/1_Curtis_Cash_Posting.py:
   - Add "Add to Patterns" button next to each match
   - On click: save (bank_description → customer_code) pattern

3. Modify app.py:
   - Load learned patterns on startup
   - Pass to orchestrator for use in matching

Patterns should persist between sessions.
```

---

## JOB 7: Add Remittance Upload UI (P2)
**Estimated Time:** 3-5 hours
**Files to Modify:**
- `app.py` (MODIFY)
- `src/matching/layer0_remittance.py` (MODIFY if needed)

**Tasks:**
1. Add file uploader for remittance PDFs in sidebar
2. Parse uploaded PDFs immediately
3. Store parsed remittances in session state
4. Use in matching when processing bank file

**Prompt for Agent:**
```
You are adding remittance upload functionality to the Liquidline app.

CURRENT STATE: Remittance PDFs must be manually placed in a folder.
TARGET STATE: Users can drag-drop remittance PDFs in the Streamlit UI.

IMPLEMENTATION:
1. In app.py sidebar, add:
   - st.file_uploader for multiple PDF files
   - "Upload Remittances" section above "Reference Data"

2. When PDFs uploaded:
   - Parse using RemittanceParser from src/matching/remittance_parser.py
   - Store parsed data in st.session_state.remittances

3. When processing bank file:
   - Pass remittances to orchestrator
   - Layer 0 should match against uploaded remittances

Test with sample remittance PDFs in remittance_examples/ folder.
```

---

## EXECUTION ORDER

### Phase 1: Critical Fixes (Before Client Demo)
1. **Job 1** - Fix KPIs & Export Logic (AGENT)
2. **Job 2** - Configure Streamlit Secrets (USER MANUAL)

### Phase 2: Integration (Before Sign-off)
3. **Job 4** - Test Eagle Import (USER MANUAL - needs Karen)
4. **Job 3** - Invoice-to-Customer Lookup (AGENT)

### Phase 3: Documentation (Before Training)
5. **Job 5** - Create Documentation & Video (AGENT)

### Phase 4: Enhancements (Post-Delivery)
6. **Job 6** - Pattern Learning (AGENT)
7. **Job 7** - Remittance Upload UI (AGENT)

---

## SUCCESS METRICS

After all fixes:
- [ ] "Postable rate" shown in UI (not just "match rate")
- [ ] Export only includes rows with customer codes
- [ ] SI-only matches without codes marked MEDIUM
- [ ] Login required to access app
- [ ] Layer 4 AI working
- [ ] Eagle import tested successfully
- [ ] Documentation complete with screenshots
- [ ] Video walkthrough recorded
- [ ] Pattern learning saves new patterns
- [ ] Remittance PDFs uploadable via UI
