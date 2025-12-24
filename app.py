"""
Liquidline Bank Reconciliation Automation
Streamlit Dashboard Application

Main entry point for the automation system.
Provides interface for Curtis (Cash Posting) and Erin (Bank Reconciliation)
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Liquidline Bank Automation",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import our modules
from config import (
    DATA_DIR, OUTPUT_DIR, AKA_SHEET_PATH, CUSTOMER_REPORT_PATH,
    CONFIDENCE_THRESHOLDS
)
from src.parsers.bank_parser import BankParser
from src.data.customer_loader import CustomerLoader
from src.data.aka_loader import AKALoader
from src.matching.orchestrator import MatchingOrchestrator
from src.output.excel_generator import ExcelGenerator
from src.models.transaction import ConfidenceLevel


# Initialize session state
if 'transactions' not in st.session_state:
    st.session_state.transactions = []
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False


def load_reference_data():
    """Load customer and AKA data"""
    with st.spinner("Loading reference data..."):
        # Load customer data
        customer_loader = None
        if CUSTOMER_REPORT_PATH.exists():
            try:
                customer_loader = CustomerLoader(CUSTOMER_REPORT_PATH)
                st.success(f"✅ Loaded {len(customer_loader.customers)} customers")
            except Exception as e:
                st.warning(f"⚠️ Could not load customer data: {e}")

        # Load AKA patterns
        aka_loader = None
        if AKA_SHEET_PATH.exists():
            try:
                aka_loader = AKALoader(AKA_SHEET_PATH)
                st.success(f"✅ Loaded {len(aka_loader.patterns)} AKA patterns")
            except Exception as e:
                st.warning(f"⚠️ Could not load AKA patterns: {e}")

        # Initialize orchestrator
        st.session_state.orchestrator = MatchingOrchestrator(
            customer_loader=customer_loader,
            aka_loader=aka_loader
        )
        st.session_state.data_loaded = True


def render_sidebar():
    """Render sidebar with data loading and stats"""
    with st.sidebar:
        st.title("💰 Liquidline")
        st.subheader("Bank Reconciliation Automation")

        st.divider()

        # Data loading section
        st.subheader("📁 Reference Data")

        if not st.session_state.data_loaded:
            if st.button("Load Reference Data", type="primary"):
                load_reference_data()
        else:
            st.success("Reference data loaded")

            if st.session_state.orchestrator:
                orch = st.session_state.orchestrator

                if orch.customer_loader:
                    st.metric("Customers", len(orch.customer_loader.customers))

                if orch.aka_loader:
                    st.metric("AKA Patterns", len(orch.aka_loader.patterns))

        st.divider()

        # Statistics
        if st.session_state.transactions:
            st.subheader("📊 Current Batch Stats")
            transactions = st.session_state.transactions

            total = len(transactions)
            matched = sum(1 for t in transactions if t.match_result)
            high = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH)
            medium = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM)
            low = sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.LOW)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", total)
                st.metric("🟢 High", high)
            with col2:
                st.metric("Matched", f"{matched/total*100:.0f}%" if total else "0%")
                st.metric("🟡 Medium", medium)

            st.metric("🔴 Low/Unmatched", low + (total - matched))

        st.divider()

        # Info
        st.caption("v1.0 | BrandedAI")


def render_upload_section():
    """Render bank file upload section"""
    st.header("📤 Upload Bank Download")

    uploaded_file = st.file_uploader(
        "Upload Lloyds Bank CSV file",
        type=['csv'],
        help="Upload the daily bank download CSV file from Lloyds"
    )

    # Or select from existing files
    st.write("**Or select from existing files:**")

    csv_files = list(DATA_DIR.glob("*.csv"))
    if csv_files:
        selected_file = st.selectbox(
            "Select existing bank file",
            options=[""] + [f.name for f in csv_files],
            format_func=lambda x: x if x else "-- Select a file --"
        )
    else:
        selected_file = None
        st.info("No CSV files found in data directory")

    # Process button
    col1, col2 = st.columns([1, 3])
    with col1:
        process_btn = st.button("🚀 Process Transactions", type="primary")

    if process_btn:
        file_to_process = None

        if uploaded_file:
            # Save uploaded file temporarily
            temp_path = DATA_DIR / uploaded_file.name
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            file_to_process = temp_path
        elif selected_file:
            file_to_process = DATA_DIR / selected_file

        if file_to_process:
            process_bank_file(file_to_process)
        else:
            st.error("Please upload or select a file to process")


def process_bank_file(file_path: Path):
    """Process a bank file through the matching engine"""
    if not st.session_state.data_loaded:
        st.error("Please load reference data first")
        return

    with st.spinner(f"Processing {file_path.name}..."):
        try:
            # Parse bank file
            parser = BankParser()
            transactions = parser.parse_file(file_path)

            st.info(f"Parsed {len(transactions)} transactions")

            # Run matching
            orchestrator = st.session_state.orchestrator
            matched_transactions = orchestrator.match_transactions(transactions)

            st.session_state.transactions = matched_transactions

            # Show stats
            stats = orchestrator.get_stats()
            st.success(f"✅ Matching complete! Match rate: {stats.get('match_rate', 0):.1f}%")

        except Exception as e:
            st.error(f"Error processing file: {e}")
            logger.exception("Processing error")


def render_results_section():
    """Render matching results"""
    if not st.session_state.transactions:
        st.info("No transactions processed yet. Upload a bank file to get started.")
        return

    st.header("📋 Matching Results")

    transactions = st.session_state.transactions

    # Filter tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🟢 High Confidence ({sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH)})",
        f"🟡 Medium ({sum(1 for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM)})",
        f"🔴 Low/Exception ({sum(1 for t in transactions if not t.match_result or t.match_result.confidence_level == ConfidenceLevel.LOW)})",
        "📊 All Transactions"
    ])

    with tab1:
        high_conf = [t for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.HIGH]
        render_transaction_table(high_conf, "high")

    with tab2:
        medium_conf = [t for t in transactions if t.match_result and t.match_result.confidence_level == ConfidenceLevel.MEDIUM]
        render_transaction_table(medium_conf, "medium")

    with tab3:
        low_conf = [t for t in transactions if not t.match_result or t.match_result.confidence_level == ConfidenceLevel.LOW]
        render_transaction_table(low_conf, "low")

    with tab4:
        render_transaction_table(transactions, "all")


def render_transaction_table(transactions, filter_type: str):
    """Render a table of transactions"""
    if not transactions:
        st.info("No transactions in this category")
        return

    # Build dataframe
    rows = []
    for t in transactions:
        match = t.match_result
        rows.append({
            "Date": t.post_date.strftime("%d/%m/%Y"),
            "Amount": f"£{t.amount:,.2f}",
            "Reference": t.customer_reference[:30] + "..." if len(t.customer_reference) > 30 else t.customer_reference,
            "Detail": t.transaction_detail[:30] + "..." if len(t.transaction_detail) > 30 else t.transaction_detail,
            "Customer Code": match.customer_code if match else "",
            "Customer Name": match.customer_name[:25] + "..." if match and len(match.customer_name) > 25 else (match.customer_name if match else ""),
            "Confidence": f"{match.confidence_score * 100:.0f}%" if match else "0%",
            "Method": match.match_method.value if match else "unmatched",
            "Invoices": "; ".join([a.invoice_number for a in match.invoice_allocations]) if match and match.invoice_allocations else ""
        })

    df = pd.DataFrame(rows)

    # Display with custom styling
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount": st.column_config.TextColumn("Amount", width="small"),
            "Confidence": st.column_config.TextColumn("Conf", width="small"),
        }
    )


def render_export_section():
    """Render export options"""
    if not st.session_state.transactions:
        return

    st.header("📥 Export Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Export Curtis Review", type="primary"):
            export_curtis_review()

    with col2:
        if st.button("📤 Export Eagle Import"):
            export_eagle_import()

    with col3:
        if st.button("📋 Export All Data"):
            export_all_data()


def export_curtis_review():
    """Export Curtis review spreadsheet"""
    generator = ExcelGenerator(OUTPUT_DIR)
    output_path = generator.generate_curtis_review(st.session_state.transactions)
    st.success(f"✅ Exported to: {output_path}")

    # Provide download
    with open(output_path, 'rb') as f:
        st.download_button(
            label="⬇️ Download Excel File",
            data=f.read(),
            file_name=output_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def export_eagle_import():
    """Export Eagle import file"""
    generator = ExcelGenerator(OUTPUT_DIR)
    output_path = generator.generate_eagle_import(st.session_state.transactions)
    st.success(f"✅ Exported to: {output_path}")

    with open(output_path, 'rb') as f:
        st.download_button(
            label="⬇️ Download Eagle Import",
            data=f.read(),
            file_name=output_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def export_all_data():
    """Export all transaction data"""
    transactions = st.session_state.transactions

    rows = [t.to_dict() for t in transactions]
    df = pd.DataFrame(rows)

    csv = df.to_csv(index=False)
    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )


def main():
    """Main application entry point"""
    render_sidebar()

    # Main content
    st.title("Liquidline Bank Reconciliation Automation")
    st.markdown("*Intelligent matching system for cash posting and bank reconciliation*")

    st.divider()

    # Check if data is loaded
    if not st.session_state.data_loaded:
        st.warning("👈 Please load reference data from the sidebar to get started")
        st.stop()

    # Main sections
    render_upload_section()

    st.divider()

    render_results_section()

    st.divider()

    render_export_section()

    # Footer
    st.divider()
    st.caption("Liquidline Bank Automation v1.0 | BrandedAI")


if __name__ == "__main__":
    main()
