# Liquidline Bank Reconciliation Automation
## Quick Start Guide

**Version:** 1.0
**Last Updated:** December 2025

---

## Overview

This system automates the matching of bank transactions to customer accounts, reducing manual cash posting time by up to 70%. The system uses a 4-layer matching engine:

1. **SI Invoice Pattern** - Matches SI-XXXXXX invoice numbers
2. **AKA Pattern** - Matches known customer reference patterns
3. **Fuzzy Name** - Intelligent customer name matching
4. **AI Inference** - Handles ambiguous cases

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Internet connection (for AI layer)
- Access to bank download files (Lloyds CSV format)

### First-Time Setup

1. **Open Command Prompt** in the project folder

2. **Create virtual environment:**
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Add your OpenRouter API key:
     ```
     OPENROUTER_API_KEY=your_key_here
     ```

5. **Start the dashboard:**
   ```
   streamlit run app.py
   ```

6. **Open browser** to http://localhost:8501

---

## Daily Workflow

### For Curtis (Cash Posting)

#### Step 1: Upload Bank File
1. Download bank transactions from Lloyds (CSV format)
2. Open the dashboard (http://localhost:8501)
3. Click "Browse files" or drag the CSV file
4. Click "Process Transactions"

#### Step 2: Review Matches
1. Go to **Curtis Cash Posting** page (sidebar)
2. Review the summary statistics:
   - GREEN = High confidence (ready for approval)
   - YELLOW = Medium confidence (quick review)
   - RED = Low confidence (needs investigation)

#### Step 3: Approve & Export
1. Click **"Approve All High Confidence"** for GREEN matches
2. Review YELLOW items individually if time permits
3. Click **"Generate Eagle Import File"**
4. Download the Excel file
5. Import into Eagle using standard process

### For Erin (Bank Reconciliation)

#### Step 1: View Reconciliation Summary
1. Open the dashboard
2. Go to **Erin's Reconciliation** page (sidebar)
3. Review:
   - Total transactions processed
   - Match rate percentage
   - Items requiring review

#### Step 2: Investigate Discrepancies
1. Check the **"Needs Review"** tab for:
   - Unmatched transactions
   - Low confidence matches
2. Export items to Excel for investigation

#### Step 3: Audit Trail
1. Use the **"Full Audit Trail"** tab
2. Filter by match method or confidence
3. Export full report if needed

---

## Understanding Confidence Levels

| Level | Color | Meaning | Action |
|-------|-------|---------|--------|
| HIGH | GREEN | 90%+ match confidence | One-click approve |
| MEDIUM | YELLOW | 75-90% confidence | Quick verify |
| LOW | RED | <75% confidence | Manual check |
| UNMATCHED | - | No match found | Investigate |

---

## Match Methods Explained

### Layer 1: SI Invoice
- Looks for patterns like `SI-123456` in the transaction
- Highest accuracy for invoice payments
- Green = definite match

### Layer 2: AKA Pattern
- Uses the historical AKA reference sheet (551 patterns)
- Matches known customer payment patterns
- Very reliable for repeat customers

### Layer 3: Fuzzy Name
- Intelligent name matching (handles typos, abbreviations)
- Removes suffixes like LTD, Limited, PLC
- Finds "FREIGHTLINER LTD" even if stored as "Freightliner Limited"

### Layer 4: AI Inference
- Uses AI to analyze ambiguous transactions
- Considers multiple factors
- Good for complex Group payments

---

## Common Tasks

### Processing Multiple Days

The system can process multiple bank files. For each day:
1. Upload the day's bank CSV
2. Process and approve
3. Export Eagle file

### Exporting Reports

**Curtis Review Spreadsheet:**
- Color-coded by confidence
- Shows all match details
- For review before Eagle import

**Eagle Import File:**
- Formatted for Eagle ERP
- Contains customer codes
- Ready for import

### Handling Unmatched Transactions

1. Check the customer reference for typos
2. Search the AKA sheet for similar patterns
3. Manually look up in Eagle
4. Add to AKA sheet for future matching

---

## Troubleshooting

### Dashboard Won't Start
```
# Make sure virtual environment is active
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt

# Try starting again
streamlit run app.py
```

### Low Match Rate
1. Ensure customer data is up to date
2. Check if bank format has changed
3. Verify AKA sheet is loaded correctly

### AI Layer Not Working
1. Check API key in `.env` file
2. Verify internet connection
3. Check API quota/credits

### Transaction Detail Too Long
Bank truncates long names. The fuzzy matching handles this by using partial matching algorithms.

---

## Data Files

| File | Purpose | Location |
|------|---------|----------|
| Bank CSV | Daily bank download | Upload via dashboard |
| Customer Report.xlsx | Customer master data | data/ folder |
| ALL HISTORY 2024-2025.xlsx | AKA patterns | data/ folder |

---

## Support

For technical issues or questions:
- **Contact:** Scott Markham, BrandedAI
- **Documentation:** PROGRESS.md in project folder

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| R | Refresh dashboard |
| Ctrl+F | Search in tables |

---

## Best Practices

1. **Process daily** - Don't let transactions pile up
2. **Review YELLOW items** - They're usually correct but worth a glance
3. **Update AKA sheet** - Add new patterns you discover
4. **Export before closing** - Always generate Eagle file
5. **Check the summary** - Catch issues early

---

*Last updated: December 2025 - Liquidline Bank Reconciliation Automation v1.0*
