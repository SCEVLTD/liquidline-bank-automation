"""
Remittance Parser - Extracts payment data from remittance advice PDFs
Uses AI to handle varied formats from different companies
"""

import re
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import os


@dataclass
class RemittanceInvoice:
    """Single invoice line from a remittance"""
    invoice_number: str
    amount: float
    date: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ParsedRemittance:
    """Structured remittance data"""
    customer_name: str
    payment_date: str
    total_amount: float
    invoices: List[RemittanceInvoice]
    account_reference: Optional[str] = None
    bacs_reference: Optional[str] = None
    payment_method: str = "BACS"
    raw_text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['invoices'] = [asdict(inv) for inv in self.invoices]
        return result


class RemittanceParser:
    """
    Parses remittance advice documents to extract structured payment data.
    Uses regex patterns for common formats and AI for complex cases.
    """

    # Common invoice number patterns
    INVOICE_PATTERNS = [
        r'SI-?\d{6}',           # SI-123456 or SI123456
        r'S1-?\d{6}',           # S1-123456 (typo variant)
        r'INV-?\d+',            # INV-12345
        r'[A-Z]{2,3}\d{6,}',    # Generic alphanumeric
    ]

    # Amount patterns
    AMOUNT_PATTERN = r'[£$]?\s*[\d,]+\.?\d{0,2}'

    # Date patterns
    DATE_PATTERNS = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',      # DD/MM/YY or DD/MM/YYYY
        r'\d{1,2}\s+\w+\s+\d{4}',         # 8 Jan 2026
        r'\w+\s+\d{1,2},?\s+\d{4}',       # December 24, 2025
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')

    def extract_invoices_regex(self, text: str) -> List[Dict]:
        """Extract invoice numbers and amounts using regex"""
        invoices = []

        # Find all SI invoice numbers
        for pattern in self.INVOICE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                invoice_num = match.group().upper()
                # Normalize SI format
                if invoice_num.startswith('S1'):
                    invoice_num = 'SI' + invoice_num[2:]
                if not invoice_num.startswith('SI-') and invoice_num.startswith('SI'):
                    invoice_num = 'SI-' + invoice_num[2:]

                invoices.append({
                    'invoice_number': invoice_num,
                    'position': match.start()
                })

        return invoices

    def extract_amounts(self, text: str) -> List[float]:
        """Extract monetary amounts from text"""
        amounts = []
        # Look for amounts with currency symbols or in tables
        pattern = r'[£$]?\s*([\d,]+\.\d{2})'
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                amount = float(match.group(1).replace(',', ''))
                if amount > 0:
                    amounts.append(amount)
            except ValueError:
                continue
        return amounts

    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        dates = []
        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                dates.append(match.group())
        return dates

    def extract_customer_name(self, text: str) -> Optional[str]:
        """Try to extract customer/company name"""
        # Look for common patterns
        patterns = [
            r'(?:From|Remittance from|Payment from)[:\s]+([A-Za-z0-9\s&\-\.]+?)(?:\n|Ltd|Limited)',
            r'^([A-Z][A-Za-z0-9\s&\-\.]+?(?:Ltd|Limited|PLC|Group|Council))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Return first significant line as fallback
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 5]
        if lines:
            return lines[0][:100]

        return None

    def parse_with_ai(self, text: str) -> Optional[ParsedRemittance]:
        """Use AI to parse complex remittance formats"""
        if not self.api_key:
            return None

        try:
            import requests

            prompt = f"""Extract payment information from this remittance advice. Return JSON only.

REMITTANCE TEXT:
{text[:4000]}

Return this exact JSON structure:
{{
    "customer_name": "Company name paying",
    "payment_date": "DD/MM/YYYY format",
    "total_amount": 123.45,
    "account_reference": "Account code if present or null",
    "bacs_reference": "BACS/payment ref if present or null",
    "invoices": [
        {{"invoice_number": "SI-123456", "amount": 100.00, "description": "optional"}}
    ]
}}"""

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    data = json.loads(json_match.group())

                    invoices = [
                        RemittanceInvoice(
                            invoice_number=inv.get('invoice_number', ''),
                            amount=float(inv.get('amount', 0)),
                            description=inv.get('description')
                        )
                        for inv in data.get('invoices', [])
                    ]

                    return ParsedRemittance(
                        customer_name=data.get('customer_name', 'Unknown'),
                        payment_date=data.get('payment_date', ''),
                        total_amount=float(data.get('total_amount', 0)),
                        invoices=invoices,
                        account_reference=data.get('account_reference'),
                        bacs_reference=data.get('bacs_reference'),
                        raw_text=text,
                        confidence=0.85
                    )
        except Exception as e:
            print(f"AI parsing error: {e}")

        return None

    def parse_text(self, text: str) -> ParsedRemittance:
        """Parse remittance text using regex first, then AI if needed"""

        # Try regex extraction first
        invoices_raw = self.extract_invoices_regex(text)
        amounts = self.extract_amounts(text)
        dates = self.extract_dates(text)
        customer = self.extract_customer_name(text)

        # If we found invoices with regex, try to match amounts
        if invoices_raw and amounts:
            # Simple case: same number of invoices and amounts in a table
            invoices = []
            for i, inv in enumerate(invoices_raw):
                amount = amounts[i] if i < len(amounts) else 0.0
                invoices.append(RemittanceInvoice(
                    invoice_number=inv['invoice_number'],
                    amount=amount
                ))

            total = sum(inv.amount for inv in invoices)
            if total == 0 and amounts:
                total = max(amounts)  # Likely the total row

            return ParsedRemittance(
                customer_name=customer or "Unknown",
                payment_date=dates[0] if dates else "",
                total_amount=total,
                invoices=invoices,
                raw_text=text,
                confidence=0.7
            )

        # Fall back to AI for complex formats
        ai_result = self.parse_with_ai(text)
        if ai_result:
            return ai_result

        # Last resort: return partial data
        return ParsedRemittance(
            customer_name=customer or "Unknown",
            payment_date=dates[0] if dates else "",
            total_amount=max(amounts) if amounts else 0.0,
            invoices=[],
            raw_text=text,
            confidence=0.3
        )

    def parse_pdf(self, pdf_path: str) -> ParsedRemittance:
        """Parse a PDF remittance file"""
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            full_text = '\n'.join(text_parts)
            return self.parse_text(full_text)

        except ImportError:
            # Try alternative PDF reader
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(pdf_path)
                text_parts = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                full_text = '\n'.join(text_parts)
                return self.parse_text(full_text)
            except Exception as e:
                print(f"PDF read error: {e}")
                return ParsedRemittance(
                    customer_name="Unknown",
                    payment_date="",
                    total_amount=0.0,
                    invoices=[],
                    raw_text="",
                    confidence=0.0
                )


def match_remittance_to_transaction(
    remittance: ParsedRemittance,
    bank_transactions: List[Dict],
    tolerance: float = 0.01
) -> Optional[Dict]:
    """
    Match a parsed remittance to a bank transaction by amount.

    Args:
        remittance: Parsed remittance data
        bank_transactions: List of bank transactions with 'amount' field
        tolerance: Amount matching tolerance (default 1p)

    Returns:
        Matched transaction or None
    """
    target_amount = remittance.total_amount

    for txn in bank_transactions:
        txn_amount = abs(float(txn.get('amount', 0)))
        if abs(txn_amount - target_amount) <= tolerance:
            return txn

    return None


# Quick test
if __name__ == "__main__":
    parser = RemittanceParser()

    # Test with sample text
    sample = """
    Group 1 Toyota Nottingham
    Remittance Advice
    Account No: L0118
    Date: 23/12/2025

    Reference   Value     Payment
    SI-802324   831.96    831.96

    Total Remittance: 831.96
    Payment Method: BACS
    """

    result = parser.parse_text(sample)
    print(f"Customer: {result.customer_name}")
    print(f"Total: £{result.total_amount}")
    print(f"Invoices: {[inv.invoice_number for inv in result.invoices]}")
    print(f"Account: {result.account_reference}")
    print(f"Confidence: {result.confidence}")
