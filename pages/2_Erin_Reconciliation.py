"""
Liquidline Bank Reconciliation Automation
Erin's Reconciliation View

Interface for Erin to validate bank reconciliation against Eagle postings.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Erin's Reconciliation - Liquidline",
    page_icon="🏦",
    layout="wide"
)

# Import shared modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUT_DIR
from src.models.transaction import ConfidenceLevel


def get_reconciliation_summary(transactions):
    """Generate reconciliation summary statistics"""
    if not transactions:
        return None

    total = len(transactions)
    matched = sum(1 for t in transactions if t.match_result)
    high_conf = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH)
    medium_conf = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM)
    low_conf = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.LOW)
    unmatched = total - matched

    total_amount = sum(t.amount for t in transactions)
    matched_amount = sum(t.amount for t in transactions if t.match_result)
    unmatched_amount = total_amount - matched_amount

    return {
        "total_transactions": total,
        "matched_count": matched,
        "unmatched_count": unmatched,
        "high_confidence": high_conf,
        "medium_confidence": medium_conf,
        "low_confidence": low_conf,
        "total_amount": total_amount,
        "matched_amount": matched_amount,
        "unmatched_amount": unmatched_amount,
        "match_rate": (matched / total * 100) if total > 0 else 0
    }


def render_reconciliation_dashboard():
    """Main reconciliation dashboard"""
    st.title("🏦 Bank Reconciliation Dashboard")
    st.markdown("*Erin's interface for validating bank transactions against Eagle postings*")

    st.divider()

    # Check for transactions in session state
    if 'transactions' not in st.session_state or not st.session_state.transactions:
        st.warning("⚠️ No transactions loaded. Please process a bank file from the main dashboard first.")
        st.info("👈 Go to the main dashboard and upload/process a bank file to get started.")
        return

    transactions = st.session_state.transactions
    summary = get_reconciliation_summary(transactions)

    # Summary metrics
    st.subheader("📊 Reconciliation Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Transactions",
            summary["total_transactions"],
            help="Total bank transactions to reconcile"
        )

    with col2:
        st.metric(
            "Match Rate",
            f"{summary['match_rate']:.1f}%",
            delta=f"{summary['matched_count']} matched",
            delta_color="normal"
        )

    with col3:
        st.metric(
            "Requires Review",
            summary["medium_confidence"] + summary["low_confidence"] + summary["unmatched_count"],
            help="Medium/Low confidence + unmatched items"
        )

    with col4:
        st.metric(
            "Ready to Post",
            summary["high_confidence"],
            help="High confidence matches ready for Eagle"
        )

    st.divider()

    # Amount summary
    st.subheader("💰 Amount Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Bank Amount", f"£{summary['total_amount']:,.2f}")

    with col2:
        st.metric("Matched Amount", f"£{summary['matched_amount']:,.2f}")

    with col3:
        st.metric(
            "Unreconciled Amount",
            f"£{summary['unmatched_amount']:,.2f}",
            delta_color="inverse" if summary['unmatched_amount'] > 0 else "off"
        )

    st.divider()

    # Reconciliation tabs
    render_reconciliation_tabs(transactions)


def render_reconciliation_tabs(transactions):
    """Render the main reconciliation work tabs"""

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔴 Needs Review",
        "🟡 Medium Confidence",
        "🟢 Ready to Post",
        "📋 Full Audit Trail"
    ])

    with tab1:
        render_needs_review(transactions)

    with tab2:
        render_medium_confidence(transactions)

    with tab3:
        render_ready_to_post(transactions)

    with tab4:
        render_audit_trail(transactions)


def render_needs_review(transactions):
    """Render items that need manual review"""
    st.subheader("🔴 Items Requiring Manual Review")
    st.caption("These items are unmatched or have low confidence and need your attention.")

    # Filter for review items
    review_items = [
        t for t in transactions
        if not t.match_result or t.match_result.confidence_level == ConfidenceLevel.LOW
    ]

    if not review_items:
        st.success("✅ No items requiring review! All transactions have been matched.")
        return

    st.warning(f"⚠️ {len(review_items)} items need review")

    # Build dataframe
    rows = []
    for t in review_items:
        match = t.match_result
        rows.append({
            "Date": t.post_date.strftime("%d/%m/%Y"),
            "Amount": f"£{t.amount:,.2f}",
            "Customer Reference": t.customer_reference[:40] if t.customer_reference else "",
            "Transaction Detail": t.transaction_detail[:40] if t.transaction_detail else "",
            "Suggested Match": match.customer_name[:30] if match else "NO MATCH",
            "Confidence": f"{match.confidence_score * 100:.0f}%" if match else "0%",
            "Issue": "Low Confidence" if match else "Unmatched",
            "Type": t.transaction_type
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export option
    if st.button("📥 Export Review Items to Excel", key="export_review"):
        export_to_excel(review_items, "Review_Items")


def render_medium_confidence(transactions):
    """Render medium confidence matches"""
    st.subheader("🟡 Medium Confidence Matches")
    st.caption("These matches are likely correct but should be verified before posting.")

    medium_items = [
        t for t in transactions
        if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM
    ]

    if not medium_items:
        st.info("No medium confidence matches.")
        return

    st.info(f"ℹ️ {len(medium_items)} items with medium confidence")

    rows = []
    for t in medium_items:
        match = t.match_result
        rows.append({
            "Date": t.post_date.strftime("%d/%m/%Y"),
            "Amount": f"£{t.amount:,.2f}",
            "Customer Reference": t.customer_reference[:35] if t.customer_reference else "",
            "Matched To": f"{match.customer_code} - {match.customer_name[:25]}",
            "Confidence": f"{match.confidence_score * 100:.0f}%",
            "Method": match.match_method.value,
            "Details": match.match_details[:30] if match.match_details else ""
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_ready_to_post(transactions):
    """Render high confidence matches ready for Eagle posting"""
    st.subheader("🟢 Ready to Post to Eagle")
    st.caption("High confidence matches that can be posted to Eagle with minimal review.")

    high_items = [
        t for t in transactions
        if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH
    ]

    if not high_items:
        st.info("No high confidence matches yet.")
        return

    st.success(f"✅ {len(high_items)} transactions ready for posting")

    # Summary by customer
    customer_summary = {}
    for t in high_items:
        code = t.match_result.customer_code
        name = t.match_result.customer_name
        key = f"{code} - {name[:30]}"
        if key not in customer_summary:
            customer_summary[key] = {"count": 0, "total": 0.0}
        customer_summary[key]["count"] += 1
        customer_summary[key]["total"] += t.amount

    st.write("**Summary by Customer:**")
    summary_df = pd.DataFrame([
        {"Customer": k, "Transactions": v["count"], "Total Amount": f"£{v['total']:,.2f}"}
        for k, v in sorted(customer_summary.items(), key=lambda x: x[1]["total"], reverse=True)
    ])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Detailed view toggle
    if st.checkbox("Show detailed transaction list", key="show_high_detail"):
        rows = []
        for t in high_items:
            match = t.match_result
            rows.append({
                "Date": t.post_date.strftime("%d/%m/%Y"),
                "Amount": f"£{t.amount:,.2f}",
                "Customer Code": match.customer_code,
                "Customer Name": match.customer_name[:30],
                "Method": match.match_method.value,
                "Invoices": "; ".join([a.invoice_number for a in match.invoice_allocations]) if match.invoice_allocations else ""
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_audit_trail(transactions):
    """Render full audit trail of all transactions"""
    st.subheader("📋 Full Audit Trail")
    st.caption("Complete list of all transactions and their matching status.")

    # Filter options
    col1, col2 = st.columns(2)

    with col1:
        filter_method = st.multiselect(
            "Filter by Match Method",
            options=["si_invoice", "aka_pattern", "fuzzy_name", "ai_inference", "unmatched"],
            default=[]
        )

    with col2:
        filter_confidence = st.multiselect(
            "Filter by Confidence",
            options=["HIGH", "MEDIUM", "LOW", "UNMATCHED"],
            default=[]
        )

    # Apply filters
    filtered = transactions
    if filter_method:
        filtered = [
            t for t in filtered
            if (not t.match_result and "unmatched" in filter_method) or
               (t.match_result and t.match_result.match_method.value in filter_method)
        ]

    if filter_confidence:
        filtered = [
            t for t in filtered
            if (not t.match_result and "UNMATCHED" in filter_confidence) or
               (t.match_result and t.match_result.confidence_level.name in filter_confidence)
        ]

    st.write(f"Showing {len(filtered)} of {len(transactions)} transactions")

    rows = []
    for t in filtered:
        match = t.match_result
        rows.append({
            "Date": t.post_date.strftime("%d/%m/%Y"),
            "Amount": f"£{t.amount:,.2f}",
            "Type": t.transaction_type,
            "Customer Ref": t.customer_reference[:25] if t.customer_reference else "",
            "Detail": t.transaction_detail[:25] if t.transaction_detail else "",
            "Status": "✅ Matched" if match else "❌ Unmatched",
            "Customer Code": match.customer_code if match else "",
            "Customer Name": match.customer_name[:20] if match else "",
            "Confidence": match.confidence_level.name if match else "N/A",
            "Method": match.match_method.value if match else "N/A"
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export full audit
    if st.button("📥 Export Full Audit Trail", key="export_audit"):
        export_to_excel(filtered, "Audit_Trail")


def export_to_excel(transactions, prefix: str):
    """Export transactions to Excel"""
    rows = []
    for t in transactions:
        match = t.match_result
        rows.append({
            "Date": t.post_date.strftime("%d/%m/%Y"),
            "Amount": t.amount,
            "Type": t.transaction_type,
            "Customer Reference": t.customer_reference,
            "Transaction Detail": t.transaction_detail,
            "Matched": "Yes" if match else "No",
            "Customer Code": match.customer_code if match else "",
            "Customer Name": match.customer_name if match else "",
            "Confidence Score": match.confidence_score if match else 0,
            "Confidence Level": match.confidence_level.name if match else "UNMATCHED",
            "Match Method": match.match_method.value if match else "",
            "Match Details": match.match_details if match else ""
        })

    df = pd.DataFrame(rows)
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    filepath = OUTPUT_DIR / filename
    df.to_excel(filepath, index=False)
    st.success(f"✅ Exported to: {filepath}")

    with open(filepath, 'rb') as f:
        st.download_button(
            label="⬇️ Download Excel File",
            data=f.read(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# Main
render_reconciliation_dashboard()
