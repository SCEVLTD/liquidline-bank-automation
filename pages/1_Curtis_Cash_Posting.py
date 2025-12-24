"""
Liquidline Bank Reconciliation Automation
Curtis's Cash Posting Interface

Interface for Curtis to review, approve, and export cash posting data.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Curtis Cash Posting - Liquidline",
    page_icon="💰",
    layout="wide"
)

# Import shared modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUT_DIR
from src.models.transaction import ConfidenceLevel
from src.output.excel_generator import ExcelGenerator


def render_cash_posting_dashboard():
    """Main cash posting dashboard for Curtis"""
    st.title("💰 Cash Posting Dashboard")
    st.markdown("*Curtis's interface for reviewing and approving customer matches*")

    st.divider()

    # Check for transactions
    if 'transactions' not in st.session_state or not st.session_state.transactions:
        st.warning("⚠️ No transactions loaded. Please process a bank file from the main dashboard first.")
        st.info("👈 Go to the main dashboard and upload/process a bank file to get started.")
        return

    transactions = st.session_state.transactions

    # Quick stats
    render_quick_stats(transactions)

    st.divider()

    # Main workflow tabs
    tab1, tab2, tab3 = st.tabs([
        "✅ Quick Approve (High Confidence)",
        "🔍 Review Required",
        "📤 Export for Eagle"
    ])

    with tab1:
        render_quick_approve(transactions)

    with tab2:
        render_review_section(transactions)

    with tab3:
        render_export_section(transactions)


def render_quick_stats(transactions):
    """Render quick statistics"""
    total = len(transactions)
    high = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH)
    medium = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM)
    low = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.LOW)
    unmatched = sum(1 for t in transactions if not t.match_result)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total", total)
    with col2:
        st.metric("🟢 High", high, help="Ready for one-click approval")
    with col3:
        st.metric("🟡 Medium", medium, help="Needs quick review")
    with col4:
        st.metric("🔴 Low", low, help="Needs manual verification")
    with col5:
        st.metric("❌ Unmatched", unmatched, help="Requires manual matching")


def render_quick_approve(transactions):
    """Render one-click approval for high confidence matches"""
    st.subheader("✅ One-Click Approval")
    st.caption("High confidence matches that can be approved in bulk for Eagle posting.")

    high_conf = [
        t for t in transactions
        if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH
    ]

    if not high_conf:
        st.info("No high confidence matches available.")
        return

    # Summary
    total_amount = sum(t.amount for t in high_conf)
    st.success(f"✅ {len(high_conf)} transactions (£{total_amount:,.2f}) ready for approval")

    # Group by match method
    st.write("**Breakdown by Match Method:**")
    method_summary = {}
    for t in high_conf:
        method = t.match_result.match_method.value
        if method not in method_summary:
            method_summary[method] = {"count": 0, "amount": 0.0}
        method_summary[method]["count"] += 1
        method_summary[method]["amount"] += t.amount

    for method, data in method_summary.items():
        st.write(f"  - **{method}:** {data['count']} transactions (£{data['amount']:,.2f})")

    st.divider()

    # Approval action
    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("✅ Approve All High Confidence", type="primary", use_container_width=True):
            # Mark as approved in session state
            if 'approved_transactions' not in st.session_state:
                st.session_state.approved_transactions = set()

            for t in high_conf:
                st.session_state.approved_transactions.add(id(t))

            st.success(f"✅ Approved {len(high_conf)} transactions!")
            st.balloons()

    with col2:
        if st.button("📥 Export Approved to Eagle Format", use_container_width=True):
            export_eagle_format(high_conf)

    # Show preview
    if st.checkbox("Show detailed preview", key="preview_high"):
        rows = []
        for t in high_conf:
            m = t.match_result
            rows.append({
                "Date": t.post_date.strftime("%d/%m/%Y"),
                "Amount": f"£{t.amount:,.2f}",
                "Customer Code": m.customer_code,
                "Customer Name": m.customer_name[:30],
                "Method": m.match_method.value,
                "Reference": t.customer_reference[:25] if t.customer_reference else ""
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_review_section(transactions):
    """Render items needing review"""
    st.subheader("🔍 Items Requiring Review")

    # Medium confidence
    st.write("### 🟡 Medium Confidence Matches")
    st.caption("Likely correct but please verify before approving.")

    medium = [
        t for t in transactions
        if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM
    ]

    if medium:
        for i, t in enumerate(medium[:20]):  # Show first 20
            m = t.match_result
            with st.expander(f"£{t.amount:,.2f} - {t.customer_reference[:30] if t.customer_reference else 'No ref'}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Transaction:**")
                    st.write(f"- Date: {t.post_date.strftime('%d/%m/%Y')}")
                    st.write(f"- Amount: £{t.amount:,.2f}")
                    st.write(f"- Reference: {t.customer_reference}")
                    st.write(f"- Detail: {t.transaction_detail}")

                with col2:
                    st.write("**Suggested Match:**")
                    st.write(f"- Customer: {m.customer_code} - {m.customer_name}")
                    st.write(f"- Confidence: {m.confidence_score * 100:.0f}%")
                    st.write(f"- Method: {m.match_method.value}")
                    st.write(f"- Details: {m.match_details}")

                    # Alternatives if available
                    if m.alternative_matches:
                        st.write("**Alternative matches:**")
                        for alt in m.alternative_matches[:3]:
                            st.write(f"  - {alt.get('customer_code')} - {alt.get('customer_name', '')[:25]}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✅ Approve", key=f"approve_{i}"):
                        st.success("Approved!")
                with col2:
                    if st.button("🔄 Change Match", key=f"change_{i}"):
                        st.info("Manual match selection coming soon")
                with col3:
                    if st.button("⏭️ Skip", key=f"skip_{i}"):
                        st.info("Skipped")

        if len(medium) > 20:
            st.info(f"Showing first 20 of {len(medium)} medium confidence items")
    else:
        st.success("No medium confidence items to review!")

    st.divider()

    # Low confidence and unmatched
    st.write("### 🔴 Low Confidence & Unmatched")
    st.caption("These require manual investigation.")

    low_unmatched = [
        t for t in transactions
        if not t.match_result or t.match_result.confidence_level == ConfidenceLevel.LOW
    ]

    if low_unmatched:
        rows = []
        for t in low_unmatched:
            m = t.match_result
            rows.append({
                "Date": t.post_date.strftime("%d/%m/%Y"),
                "Amount": f"£{t.amount:,.2f}",
                "Reference": t.customer_reference[:30] if t.customer_reference else "",
                "Detail": t.transaction_detail[:30] if t.transaction_detail else "",
                "Status": "Low Confidence" if m else "Unmatched",
                "Suggested": f"{m.customer_code} - {m.customer_name[:20]}" if m else "None"
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.success("No low confidence or unmatched items!")


def render_export_section(transactions):
    """Render export options"""
    st.subheader("📤 Export for Eagle")
    st.caption("Generate files for importing into Eagle ERP.")

    # Filter options
    st.write("**Select what to export:**")

    export_high = st.checkbox("Include High Confidence matches", value=True)
    export_medium = st.checkbox("Include Medium Confidence matches", value=False)
    export_low = st.checkbox("Include Low Confidence matches", value=False)

    # Filter transactions
    export_list = []
    for t in transactions:
        if not t.match_result:
            continue
        if t.match_result.confidence_level == ConfidenceLevel.HIGH and export_high:
            export_list.append(t)
        elif t.match_result.confidence_level == ConfidenceLevel.MEDIUM and export_medium:
            export_list.append(t)
        elif t.match_result.confidence_level == ConfidenceLevel.LOW and export_low:
            export_list.append(t)

    if export_list:
        total_amount = sum(t.amount for t in export_list)
        st.info(f"Ready to export: {len(export_list)} transactions (£{total_amount:,.2f})")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Generate Curtis Review File", type="primary", use_container_width=True):
                export_curtis_review(export_list)

        with col2:
            if st.button("📤 Generate Eagle Import File", use_container_width=True):
                export_eagle_format(export_list)
    else:
        st.warning("No transactions selected for export. Check the filters above.")


def export_curtis_review(transactions):
    """Export Curtis review spreadsheet"""
    try:
        generator = ExcelGenerator(OUTPUT_DIR)
        output_path = generator.generate_curtis_review(
            transactions,
            filename=f"Curtis_Review_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        st.success(f"✅ Generated: {output_path.name}")

        with open(output_path, 'rb') as f:
            st.download_button(
                label="⬇️ Download Curtis Review",
                data=f.read(),
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error generating file: {e}")


def export_eagle_format(transactions):
    """Export Eagle import format"""
    try:
        generator = ExcelGenerator(OUTPUT_DIR)
        output_path = generator.generate_eagle_import(
            transactions,
            filename=f"Eagle_Import_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        st.success(f"✅ Generated: {output_path.name}")

        with open(output_path, 'rb') as f:
            st.download_button(
                label="⬇️ Download Eagle Import",
                data=f.read(),
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error generating file: {e}")


# Main
render_cash_posting_dashboard()
