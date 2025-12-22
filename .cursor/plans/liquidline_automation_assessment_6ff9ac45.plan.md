---
name: Liquidline Automation Assessment
overview: Technical feasibility assessment and implementation roadmap for automating Liquidline's cash posting and bank reconciliation workflows. This plan provides honest timeline and budget estimates based on detailed analysis of actual data files and workflow complexity.
todos:
  - id: eagle-access-confirm
    content: Confirm Eagle export/import capability with Matt before proposal
    status: pending
  - id: create-proposal-doc
    content: Create client proposal document with 8-week timeline and £19,500 budget
    status: pending
  - id: setup-infrastructure
    content: Set up Supabase database and n8n instance for development
    status: pending
  - id: build-bank-parser
    content: Build bank file parser for Lloyds CSV format
    status: pending
  - id: create-matching-engine
    content: Develop AI customer matching engine with Claude API
    status: pending
  - id: build-output-generator
    content: Build Excel output generator matching Curtis's format
    status: pending
  - id: implement-group-one
    content: Implement Group One (169 BMW accounts) pattern matching
    status: pending
  - id: user-testing-week3
    content: Conduct user testing with Curtis at Week 3 milestone
    status: pending
---

# Liquidline Finance Automation - Technical Feasibility Assessment

---

## EXECUTIVE SUMMARY

**Can we deliver 70-80% automation in 6 weeks?** **CONDITIONAL YES** - but with important caveats.

| Metric | Assessment |
|--------|------------|
| **Recommended Timeline** | 8 weeks (realistic) / 6 weeks (aggressive MVP) |
| **Recommended Budget** | £16,500 - £19,500 (not £13,500) |
| **Confidence Level** | 75% for 70% automation in 8 weeks |
| **Risk Level** | MEDIUM - manageable with proper scoping |

**Key Finding from Data Analysis:** The actual bank download (21 Nov 25.csv) shows **180+ daily transactions**, not 90. However, **41 transactions (23%) have clear SI-XXXXXX invoice references** that can be auto-matched immediately. Another 30-40% have customer names/codes that can be pattern-matched. This means 60-65% automation is achievable relatively quickly.

**Recommendation:** CONDITIONAL GO with 8-week timeline at £18,000. Deliver a working 60% automation MVP at week 6, extend to 75% by week 8.

---

## PART 1: FEASIBILITY ASSESSMENT

### 1.1 Is 6 Weeks Realistic?

**CONDITIONAL YES** - but only for MVP (60-65% automation)

**What gets delivered in 6 weeks:**

- Automated bank download processing
- AI customer matching (80%+ accuracy on clear references)
- Pre-populated spreadsheet for Curtis
- Basic exception flagging
- Foundation for Erin's reconciliation

**What does NOT get delivered in 6 weeks:**

- Full Group One (169 BMW) automation
- Remittance email auto-capture (requires Outlook integration)
- All 8 exception types automated
- Eagle direct posting (likely Excel import only)

### 1.2 Automation Coverage by Timeframe

| Timeframe | Automation % | What's Included |
|-----------|--------------|-----------------|
| **Week 6 (MVP)** | 60-65% | SI-invoice matching, customer name patterns, basic AKA lookup, pre-populated spreadsheet |
| **Week 8** | 70-75% | Group One automation, remittance capture (basic), enhanced exception handling |
| **Week 10** | 75-80% | Full remittance OCR, all exception types, Erin's rec automation |
| **Week 12** | 80%+ | Polish, edge cases, user training, handoff |

### 1.3 Hard Technical Blockers Analysis

**BLOCKER 1: Eagle SQL Access**

- **Do we NEED it?** NO for MVP, HELPFUL for full scope
- **Workaround:** Excel export/import (confirmed available)
- **Risk:** Manual data entry remains for posting (Curtis validates and clicks)
- **Recommendation:** Start without SQL, add later if Matt provides access

**BLOCKER 2: AI Matching Accuracy**

- **Can Claude achieve 80%+?** YES - based on data analysis
- **Evidence:** 23% of transactions have clear SI-XXXXXX patterns (100% matchable). Another 50% have customer names in Transaction Detail field
- **Risk:** Fuzzy matching on remaining 27% may hit 60-70% accuracy
- **Mitigation:** Confidence scoring - auto-process high confidence, queue low confidence

**BLOCKER 3: Remittance Auto-Capture**

- **Realistic accuracy:** 70-75% (not 85-90% as Manus claims)
- **Challenge:** PDF formats vary widely, OCR accuracy depends on quality
- **Mitigation:** Phase 2 feature - focus on bank data matching first

**BLOCKER 4: Group One Complexity (169 BMW accounts)**

- **Automatable?** YES - 80% achievable
- **Evidence:** ACA prefix pattern visible in data (ACA KIRKCALDY BMW, ACA BLACKPOOL RENA, etc.)
- **Approach:** Pattern matching on "ACA", "GROUP 1", dealer codes
- **Risk:** 20% will need manual selection from 169 options

---

## PART 2: WEEK-BY-WEEK IMPLEMENTATION ROADMAP

### WEEK 1: Foundation & Data Pipeline

**Day 1-2: Infrastructure Setup (Scott)**

- Set up Supabase database with schema
- Configure n8n on DigitalOcean
- Create Git repo and deployment pipeline
- Document API access requirements

**Day 3-4: Data Models & Import (Scott + Donni)**

- Build bank download parser (21 Nov 25.csv format)
- Import 551 AKA sheet into Supabase
- Create customer master reference table
- Build transaction staging table

**Day 5: Testing & Validation (All)**

- Test bank file import with real data
- Validate AKA lookup functionality
- Create test suite for matching logic

**Deliverables:**

- Working n8n instance
- Supabase database with schema
- Bank file import working
- AKA sheet searchable

**Who does what:**

- Scott: Architecture, database design, n8n setup (16 hours)
- Donni: Python bank parser, data import scripts (24 hours)
- Mitch: AKA sheet import, testing (16 hours)

---

### WEEK 2: Core Matching Engine

**Day 1-2: Pattern Extraction (Scott)**

- Build SI-XXXXXX regex extractor
- Create customer name normalization
- Build reference pattern classifier

**Day 3-4: AI Matching Integration (Scott + Donni)**

- Integrate Claude API for fuzzy matching
- Build prompt templates for customer identification
- Create confidence scoring algorithm

**Day 5: AKA Sheet Integration (Mitch)**

- Build AKA lookup service
- Create pattern caching for speed
- Test against historical data

**Deliverables:**

- Pattern extractor working (SI-, customer names)
- Claude API matching returning results
- Confidence scores calculated (High/Medium/Low)
- AKA lookup integrated

**Who does what:**

- Scott: AI prompt engineering, matching logic (20 hours)
- Donni: Pattern extraction, API integration (24 hours)
- Mitch: AKA service, testing (20 hours)

---

### WEEK 3: Curtis Interface (Pre-Populated Spreadsheet)

**Day 1-2: Output Generator (Donni)**

- Build Excel output template matching Curtis's format
- Add columns: Matched Customer, Confidence, Suggested Invoice
- Color-code by confidence level

**Day 3-4: Workflow Integration (Scott)**

- Create n8n workflow: Bank download -> Process -> Excel output
- Add manual trigger for daily runs
- Build exception flagging logic

**Day 5: User Testing (Scott + Curtis)**

- Test with real 21 Nov data
- Get Curtis feedback on output format
- Identify missing edge cases

**Deliverables:**

- Excel output matching Curtis's current format
- Color-coded confidence levels
- First test with real user

**Who does what:**

- Scott: n8n workflow, user testing (16 hours)
- Donni: Excel generator, formatting (24 hours)
- Mitch: Exception flagging (16 hours)

---

### WEEK 4: Group One & Enhanced Matching

**Day 1-2: Group One Logic (Scott)**

- Build ACA prefix pattern matcher
- Create dealer code lookup (169 accounts)
- Handle consolidated payments

**Day 3-4: Historical Pattern Learning (Donni)**

- Analyze ALL HISTORY 2024-2025.xlsx
- Extract successful match patterns
- Build pattern confidence from history

**Day 5: Integration Testing (All)**

- Test full pipeline with week of data
- Measure accuracy metrics
- Document gaps and exceptions

**Deliverables:**

- Group One matching working (80%+ accuracy)
- Historical pattern learning active
- Accuracy metrics documented

**Who does what:**

- Scott: Group One business logic (20 hours)
- Donni: Historical analysis, pattern extraction (24 hours)
- Mitch: Integration testing (20 hours)

---

### WEEK 5: Exception Handling & Erin Foundation

**Day 1-2: Exception Categories (Scott + Mitch)**

- Build rule-based detection for 8 exception types
- Create exception queue in Supabase
- Add manual review interface

**Day 3-4: Erin Reconciliation Foundation (Donni)**

- Build Eagle export parser (Trial Balance format)
- Create matching algorithm (Eagle vs Bank)
- Build reconciliation status tracker

**Day 5: Integration (All)**

- Connect Curtis output to Erin's input
- Test full workflow chain
- Measure end-to-end metrics

**Deliverables:**

- Exception detection for VAT rounding, NIACS, vending, IFC
- Basic reconciliation matching working
- Exception queue for manual review

**Who does what:**

- Scott: Exception rules, business logic (16 hours)
- Donni: Erin's rec foundation (24 hours)
- Mitch: Manual review UI, testing (20 hours)

---

### WEEK 6: MVP Polish & Deployment

**Day 1-2: Bug Fixes & Edge Cases (All)**

- Fix issues from week 5 testing
- Handle discovered edge cases
- Performance optimization

**Day 3-4: Documentation & Training (Scott)**

- Write user guide for Curtis
- Create troubleshooting guide
- Document exception handling

**Day 5: MVP Demo & Sign-off (Scott)**

- Demo to Curtis and Erin
- Collect feedback
- Agree Phase 2 priorities

**Deliverables:**

- **MVP LIVE: 60-65% automation**
- User documentation
- Training completed
- Phase 2 scope agreed

**Who does what:**

- Scott: Demo, training, documentation (24 hours)
- Donni: Bug fixes, optimization (16 hours)
- Mitch: Edge cases, testing (16 hours)

---

### WEEKS 7-8: Phase 2 - Reach 75%

**Week 7 Focus:**

- Remittance email capture (basic - text parsing)
- Enhanced Group One matching
- Automated exception resolution (VAT rounding, simple cases)

**Week 8 Focus:**

- Erin's reconciliation automation
- Reporting dashboard
- Performance tuning
- User adoption support

**Deliverable: 70-75% automation achieved**

---

## PART 3: COMPONENT ARCHITECTURE

### Component 1: Bank File Processor

| Attribute | Detail |
|-----------|--------|
| **Technology** | Python + pandas |
| **Build Complexity** | Simple (2 days) |
| **Build Time** | 16 hours |
| **Success Criteria** | Parse 100% of Lloyds CSV format |
| **Who Builds** | Donni |

**Edge Cases:**

- Multi-line transaction details (seen in ExportFile)
- Special characters in references
- Currency variations (EUR, USD accounts)

**Code Modules:**

- `bank_parser.py` - CSV/XLSX parser
- `transaction_normalizer.py` - Field standardization
- `bank_file_trigger.py` - n8n webhook receiver

---

### Component 2: AI Customer Matching Engine

| Attribute | Detail |
|-----------|--------|
| **Technology** | Python + Claude API + Supabase |
| **Build Complexity** | Complex (5 days) |
| **Build Time** | 40 hours |
| **Success Criteria** | 80%+ accuracy on customer identification |
| **Who Builds** | Scott (prompts/logic) + Donni (integration) |

**Matching Hierarchy:**

1. **Exact SI- match** (23% of transactions) - 100% accuracy
2. **AKA sheet pattern** (25% of transactions) - 95% accuracy
3. **Customer name fuzzy match** (30% of transactions) - 85% accuracy
4. **Claude AI inference** (22% of transactions) - 70% accuracy

**Training Data:**

- 551 AKA patterns (immediate)
- ALL HISTORY 2024-2025.xlsx (historical matches)
- Curtis feedback loop (ongoing learning)

**Code Modules:**

- `pattern_extractor.py` - SI- and customer reference extraction
- `aka_lookup.py` - AKA sheet search service
- `claude_matcher.py` - AI inference with prompts
- `confidence_scorer.py` - Scoring algorithm
- `match_orchestrator.py` - Routing logic

---

### Component 3: Group One Handler

| Attribute | Detail |
|-----------|--------|
| **Technology** | Python + Supabase |
| **Build Complexity** | Medium (3 days) |
| **Build Time** | 24 hours |
| **Success Criteria** | 80%+ accuracy on 169 BMW accounts |
| **Who Builds** | Scott |

**Patterns Identified:**

- "ACA [LOCATION] [BRAND]" (e.g., ACA KIRKCALDY BMW)
- "GROUP 1 [BRAND]" (e.g., GROUP 1 JLR)
- Dealer codes in reference field

**Edge Cases:**

- New dealerships not in master list
- Consolidated payments across dealerships
- Ambiguous location names

---

### Component 4: Curtis Output Generator

| Attribute | Detail |
|-----------|--------|
| **Technology** | Python + openpyxl + n8n |
| **Build Complexity** | Medium (3 days) |
| **Build Time** | 24 hours |
| **Success Criteria** | Output matches Curtis's current format |
| **Who Builds** | Donni |

**Output Columns:**
| Column | Source |
|--------|--------|
| Transaction Date | Bank download |
| Bank Reference | Bank download |
| Amount | Bank download |
| **Matched Customer** | AI engine (NEW) |
| **Confidence** | AI engine (NEW - High/Med/Low) |
| **Suggested Invoice** | AI engine (NEW) |
| **Action** | AI engine (NEW - Auto/Review/Exception) |
| Posted? | Manual (Curtis) |
| Posted To | Manual (Curtis) |
| Comments | Manual (Curtis) |

---

### Component 5: Exception Manager

| Attribute | Detail |
|-----------|--------|
| **Technology** | n8n + Supabase |
| **Build Complexity** | Medium (3 days) |
| **Build Time** | 24 hours |
| **Success Criteria** | Correctly categorize 8 exception types |
| **Who Builds** | Scott + Mitch |

**Exception Types & Detection:**
| Exception | Detection Rule | Auto-Resolve? |
|-----------|---------------|---------------|
| VAT Rounding | Diff = 1-2p from invoice | YES |
| NIACS | Reference contains "NIACS" | NO (queue) |
| Vending | Reference contains "VENDING" | NO (queue) |
| IFC | Reference contains "IFC" | NO (queue) |
| Currency | Account = EUR/USD | YES (flag) |
| Consolidated | Multiple SIs in reference | NO (queue) |
| Group One | ACA/GROUP pattern | PARTIAL |
| CCO/Tower | Reference contains "CCO"/"TOWER" | NO (hold) |

---

## PART 4: EAGLE ERP INTEGRATION STRATEGY

### Option Analysis

| Option | Build Time | Risk | Recommendation |
|--------|-----------|------|----------------|
| **A: SQL Direct** | 5 days | HIGH | Not for MVP |
| **B: Excel Export/Import** | 3 days | LOW | **RECOMMENDED** |
| **C: Hybrid** | 7 days | MEDIUM | Phase 2 |

### RECOMMENDATION: Option B (Excel Export/Import)

**Why:**

1. No IT dependency on Matt for SQL access
2. Curtis already works in Excel - minimal behavior change
3. Lower risk - no direct database writes
4. Faster to implement
5. Can upgrade to hybrid later

**Workflow with Option B:**

1. System generates pre-populated Excel
2. Curtis reviews high-confidence matches
3. Curtis manually posts to Eagle (unchanged)
4. BUT: Time saved on customer lookup and matching

**Time Savings with Option B:**

- Current: 2-3 min per transaction (search + match + post)
- With automation: 30 sec per transaction (verify + post)
- **Savings: 70-80% of lookup time, 0% of posting time**
- **Net savings: ~50-60% of total time** (still significant!)

---

## PART 5: MVP vs FULL SCOPE

### MVP (Week 6) - 60-65% Automation

**Included:**

- Bank file auto-processing
- AI customer matching (high confidence)
- Pre-populated spreadsheet for Curtis
- AKA sheet integration
- Basic exception flagging
- Group One pattern matching (basic)

**Excluded:**

- Remittance email auto-capture
- Eagle direct posting
- Full exception auto-resolution
- Erin's reconciliation automation
- Currency revaluation automation

### Full Scope (Week 8-10) - 75-80% Automation

**Additional Features:**

- Remittance email parsing (text-based)
- Enhanced Group One (169 accounts)
- Exception auto-resolution (VAT, simple cases)
- Erin's rec pre-population
- Basic reporting dashboard

### Future Enhancements (Not in Project)

- Full OCR remittance parsing
- Eagle SQL direct posting
- Machine learning model retraining
- Multi-currency automation
- Predictive analytics

---

## PART 6: RISK REGISTER

### RISK 1: Eagle Access Limitations

| Attribute | Assessment |
|-----------|------------|
| **Probability** | Medium (40%) |
| **Impact** | High |
| **Mitigation** | Design for Excel-first; SQL is bonus |
| **Contingency** | If SQL required, add 2 weeks and negotiate access |

### RISK 2: AI Matching Accuracy Below 75%

| Attribute | Assessment |
|-----------|------------|
| **Probability** | Low (20%) |
| **Impact** | High |
| **Mitigation** | Week 2 pilot with real data; adjust prompts early |
| **Contingency** | Fall back to rule-based matching; reduce automation target |

### RISK 3: Group One Complexity

| Attribute | Assessment |
|-----------|------------|
| **Probability** | Medium (35%) |
| **Impact** | Medium |
| **Mitigation** | Pattern analysis in Week 4; accept 80% target |
| **Contingency** | Queue Group One for manual selection with pre-filtered options |

### RISK 4: User Adoption Resistance

| Attribute | Assessment |
|-----------|------------|
| **Probability** | Medium (30%) |
| **Impact** | High |
| **Mitigation** | Involve Curtis/Erin from Week 3; iterate on feedback |
| **Contingency** | Simplify interface; offer parallel running period |

### RISK 5: Timeline Slippage

| Attribute | Assessment |
|-----------|------------|
| **Probability** | Medium (40%) |
| **Impact** | Medium |
| **Mitigation** | Buffer in Week 6; clear MVP scope |
| **Contingency** | Deliver 60% at Week 6; extend to Week 8 for 75% |

### RISK 6: Scope Creep

| Attribute | Assessment |
|-----------|------------|
| **Probability** | High (60%) |
| **Impact** | Medium |
| **Mitigation** | Document MVP scope clearly; Change request process |
| **Contingency** | Phase 2 backlog for new requests |

### RISK 7: Offshore Dev Communication

| Attribute | Assessment |
|-----------|------------|
| **Probability** | Low (25%) |
| **Impact** | Medium |
| **Mitigation** | Daily standups; clear task specs; code reviews |
| **Contingency** | Scott picks up critical path items |

---

## PART 7: EFFORT & COST ESTIMATION

### Scott's Time

| Task | Days | Hours |
|------|------|-------|
| Architecture & design | 2 | 16 |
| AI prompt engineering | 3 | 24 |
| Business logic (matching, exceptions) | 4 | 32 |
| Group One logic | 2 | 16 |
| n8n workflow orchestration | 2 | 16 |
| Eagle integration strategy | 1 | 8 |
| User testing & iteration | 2 | 16 |
| Documentation & training | 2 | 16 |
| Project management | 2 | 16 |
| **TOTAL (6 weeks)** | **20 days** | **160 hours** |

**Scott's Cost (assuming £500/day):** £10,000

### Offshore Dev Time (Donni + Mitch)

| Task | Days | Hours |
|------|------|-------|
| Bank parser development | 3 | 24 |
| Data import scripts | 2 | 16 |
| AKA lookup service | 2 | 16 |
| Pattern extraction | 3 | 24 |
| Excel output generator | 3 | 24 |
| Exception handler | 3 | 24 |
| Testing & bug fixes | 6 | 48 |
| Erin rec foundation | 3 | 24 |
| **TOTAL (6 weeks)** | **25 days** | **200 hours** |

**Offshore Cost (at $12/hour):** $2,400 (~£1,900)

### Tools & Hosting (Monthly)

| Item | Cost/Month |
|------|-----------|
| Supabase (Pro) | £20 |
| n8n (Self-hosted on DigitalOcean) | £25 |
| Claude API (estimated 50K tokens/day) | £80 |
| DigitalOcean Droplet | £25 |
| **TOTAL Monthly** | **£150** |

**First Year Running Cost:** £1,800

### TOTAL COST TO DELIVER

| Item | 6 Weeks | 8 Weeks |
|------|---------|---------|
| Scott's time | £10,000 | £12,500 |
| Offshore time | £1,900 | £2,500 |
| Tools (3 months) | £450 | £450 |
| Buffer (10%) | £1,235 | £1,545 |
| **TOTAL COST** | **£13,585** | **£16,995** |

### RECOMMENDED CLIENT PRICING

| Package | Timeline | Automation | Price |
|---------|----------|------------|-------|
| **MVP** | 6 weeks | 60-65% | £16,500 |
| **Standard** | 8 weeks | 70-75% | £19,500 |
| **Full** | 10 weeks | 75-80% | £24,000 |

**Pricing Justification:**

- £58,500/year current manual cost
- £19,500 investment = **4-month ROI**
- 70% automation = £40,950/year savings
- **3-year value: £122,850 savings for £19,500 investment**

---

## PART 8: GO/NO-GO RECOMMENDATION

### RECOMMENDATION: CONDITIONAL GO

**Confidence Level: 75%**

**Conditions for GO:**

1. Client accepts 8-week timeline (not 6 weeks for 75%)
2. Client accepts £18,000-£19,500 budget (not £13,500)
3. Matt confirms Eagle export capability (no SQL required for MVP)
4. Curtis available for weekly testing feedback
5. Clear MVP scope documented and signed off

**Risk Level: MEDIUM (manageable)**

### Proposed Approach

**Phase 1 (Weeks 1-6): MVP Delivery - £12,000**

- Deliver 60-65% automation
- Focus on Curtis's workflow
- Pre-populated spreadsheet approach
- Weekly demos and feedback

**Phase 2 (Weeks 7-8): Enhancement - £7,500**

- Reach 70-75% automation
- Add remittance capture (basic)
- Enhance Group One
- Begin Erin automation

**Total: £19,500 for 75% automation in 8 weeks**

### Alternative if Client Insists on £13,500/6 weeks

- Deliver 55-60% automation (not 70-80%)
- Curtis's workflow only (no Erin)
- Basic matching (no Group One complexity)
- Manual remittance handling
- Clear documentation of limitations

**This is not recommended** - better to set realistic expectations upfront.

---

## CONCLUSION

This project is **technically feasible** and represents a strong ROI opportunity for Liquidline. The key is setting realistic expectations:

- **6 weeks/£13,500** = 55-60% automation (aggressive, risky)
- **8 weeks/£19,500** = 70-75% automation (recommended, achievable)
- **10 weeks/£24,000** = 75-80% automation (safe, full scope)

The data analysis shows clear automation opportunities (23% direct invoice matching, 50%+ customer name patterns), but also complexity (180+ daily transactions, 169 BMW accounts, 8 exception types) that requires adequate time to handle properly.

**Final Recommendation:** Propose 8-week engagement at £18,000-£19,500 with clear MVP milestones at Week 6. Under-promise, over-deliver.