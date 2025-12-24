# Project: Liquid Line - Bank Reconciliation Automation

## Overview
Automate 70-80% of cash posting and bank reconciliation. Signed £10,000, 50% received, January delivery.

## Client
- **Company:** Liquidline Limited (£50M, coffee/vending)
- **Contacts:** Michael Jefferies-Wilson (CFO), Karen Morphew (FD), Holly (Finance)
- **Pain:** 35-40 hrs/week manual bank rec
- **ERP:** Eagle (on-prem SQL)

## What We're Building
4-layer matching system:
1. Exact SI-invoice match (SI-XXXXXX) - 23%
2. AKA sheet lookup (551 patterns) - 25%
3. Fuzzy customer name match - 30%
4. AI inference for ambiguous - 22%

## Tech Stack
- n8n (orchestration)
- Supabase (database)
- Claude API (AI matching)
- Python (scripts)
- Excel output

## Key Files
- `data/21 Nov 25.csv` - Sample bank download
- `data/ALL HISTORY 2024-2025.xlsx` - AKA patterns
- `context/manus-analysis.md` - Full technical spec

## Status
- [x] Discovery complete
- [x] Proposal signed £10,000
- [x] 50% deposit received
- [ ] Database schema
- [ ] Bank parser
- [ ] Matching engine
- [ ] Output generator
- [ ] Testing