"""
Liquidline Bank Reconciliation Automation
AKA Sheet Loader

Loads the 551-entry AKA customer reference pattern sheet
(ALL HISTORY 2024-2025.xlsx)

This sheet maps bank reference patterns to customer codes
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import re
import logging

logger = logging.getLogger(__name__)


class AKAPattern:
    """Represents a single AKA pattern entry"""

    def __init__(self, pattern: str, customer_code: str, customer_name: str = "", notes: str = ""):
        self.pattern = pattern.strip()
        self.pattern_upper = pattern.upper().strip()
        self.customer_code = customer_code.strip().upper()
        self.customer_name = customer_name.strip()
        self.notes = notes.strip()

        # Pre-compile regex if pattern contains wildcards
        self._regex = None
        if '*' in pattern or '?' in pattern:
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            try:
                self._regex = re.compile(regex_pattern, re.IGNORECASE)
            except re.error:
                pass

    def matches(self, text: str) -> bool:
        """Check if this pattern matches the given text"""
        text_upper = text.upper().strip()

        # Try regex match first
        if self._regex:
            return bool(self._regex.search(text_upper))

        # Otherwise do substring match
        return self.pattern_upper in text_upper

    def __repr__(self):
        return f"AKAPattern({self.pattern} -> {self.customer_code})"


class AKALoader:
    """
    Loader for AKA reference pattern sheet

    The AKA sheet maps various ways customers appear in bank references
    to their actual customer codes in Eagle.

    This is Layer 2 of the matching engine.
    """

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self.patterns: List[AKAPattern] = []
        self.pattern_index: Dict[str, List[AKAPattern]] = {}  # First word index
        self.file_path = file_path
        self._loaded = False

        if file_path:
            self.load(file_path)

    def load(self, file_path: Union[str, Path]) -> int:
        """
        Load AKA patterns from Excel file

        Args:
            file_path: Path to AKA sheet xlsx

        Returns:
            Number of patterns loaded
        """
        file_path = Path(file_path)
        logger.info(f"Loading AKA patterns from: {file_path.name}")

        try:
            # Read Excel file - may have multiple sheets
            xl = pd.ExcelFile(file_path, engine='openpyxl')

            # Try to find the right sheet
            sheet_name = None
            for name in xl.sheet_names:
                if 'aka' in name.lower() or 'history' in name.lower() or 'pattern' in name.lower():
                    sheet_name = name
                    break

            if not sheet_name:
                sheet_name = xl.sheet_names[0]

            logger.info(f"Using sheet: {sheet_name}")

            df = pd.read_excel(xl, sheet_name=sheet_name)

            # Log columns found
            logger.info(f"Found columns: {list(df.columns)}")

            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()

            # Try to identify columns
            pattern_col = self._find_column(df, ['bank reference', 'pattern', 'reference', 'aka', 'bank ref'])
            code_col = self._find_column(df, ['customer code', 'code', 'customer_code', 'cust code', 'eagle code'])
            name_col = self._find_column(df, ['customer name', 'name', 'customer_name', 'cust name'])
            notes_col = self._find_column(df, ['notes', 'note', 'comments', 'comment'])

            # Fallback to positional columns
            if not pattern_col:
                pattern_col = df.columns[0]
            if not code_col and len(df.columns) > 1:
                code_col = df.columns[1]
            if not name_col and len(df.columns) > 2:
                name_col = df.columns[2]

            logger.info(f"Using columns - Pattern: {pattern_col}, Code: {code_col}, Name: {name_col}")

            # Load patterns
            for idx, row in df.iterrows():
                pattern_str = str(row.get(pattern_col, "")).strip()
                code_str = str(row.get(code_col, "")).strip() if code_col else ""
                name_str = str(row.get(name_col, "")).strip() if name_col else ""
                notes_str = str(row.get(notes_col, "")).strip() if notes_col else ""

                # Skip empty or nan values
                if not pattern_str or pattern_str.lower() == 'nan':
                    continue
                if not code_str or code_str.lower() == 'nan':
                    continue

                pattern = AKAPattern(
                    pattern=pattern_str,
                    customer_code=code_str,
                    customer_name=name_str if name_str.lower() != 'nan' else "",
                    notes=notes_str if notes_str.lower() != 'nan' else ""
                )
                self.patterns.append(pattern)

                # Build index on first word for faster lookups
                first_word = pattern_str.split()[0].upper() if pattern_str.split() else ""
                if first_word:
                    if first_word not in self.pattern_index:
                        self.pattern_index[first_word] = []
                    self.pattern_index[first_word].append(pattern)

            self._loaded = True
            logger.info(f"Loaded {len(self.patterns)} AKA patterns")

            return len(self.patterns)

        except Exception as e:
            logger.error(f"Failed to load AKA patterns: {e}")
            raise

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find a column by checking multiple possible names"""
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    def find_match(self, text: str) -> Optional[Tuple[AKAPattern, float]]:
        """
        Find the best matching AKA pattern for given text

        Args:
            text: Bank reference or transaction detail to match

        Returns:
            Tuple of (matching pattern, confidence score) or None
        """
        if not text or not self.patterns:
            return None

        text_upper = text.upper().strip()
        text_words = text_upper.split()

        best_match = None
        best_score = 0.0

        # First try indexed lookup for efficiency
        patterns_to_check = set()
        for word in text_words:
            if word in self.pattern_index:
                patterns_to_check.update(self.pattern_index[word])

        # If no indexed matches, check all patterns
        if not patterns_to_check:
            patterns_to_check = self.patterns

        # Find best match
        for pattern in patterns_to_check:
            if pattern.matches(text):
                # Calculate match quality score
                score = self._calculate_match_score(pattern, text_upper)
                if score > best_score:
                    best_score = score
                    best_match = pattern

        if best_match:
            return (best_match, best_score)

        return None

    def _calculate_match_score(self, pattern: AKAPattern, text: str) -> float:
        """
        Calculate how good a pattern match is

        Returns score between 0.0 and 1.0
        """
        pattern_len = len(pattern.pattern_upper)
        text_len = len(text)

        # Base score from pattern length ratio
        base_score = pattern_len / max(text_len, pattern_len)

        # Bonus for exact match
        if pattern.pattern_upper == text:
            return 1.0

        # Bonus for pattern at start of text
        if text.startswith(pattern.pattern_upper):
            base_score += 0.1

        # Bonus for longer patterns (more specific)
        if pattern_len > 10:
            base_score += 0.05

        return min(base_score, 0.95)  # Cap at 0.95 (exact match gets 1.0)

    def find_all_matches(self, text: str, limit: int = 5) -> List[Tuple[AKAPattern, float]]:
        """
        Find all matching AKA patterns for given text

        Args:
            text: Text to match
            limit: Maximum number of matches to return

        Returns:
            List of (pattern, score) tuples, sorted by score descending
        """
        if not text or not self.patterns:
            return []

        text_upper = text.upper().strip()
        matches = []

        for pattern in self.patterns:
            if pattern.matches(text):
                score = self._calculate_match_score(pattern, text_upper)
                matches.append((pattern, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:limit]

    def get_patterns_for_customer(self, customer_code: str) -> List[AKAPattern]:
        """Get all patterns that map to a specific customer"""
        code_upper = customer_code.upper().strip()
        return [p for p in self.patterns if p.customer_code == code_upper]

    def get_summary(self) -> dict:
        """Get summary of loaded AKA data"""
        return {
            "total_patterns": len(self.patterns),
            "unique_customers": len(set(p.customer_code for p in self.patterns)),
            "loaded": self._loaded,
            "source_file": str(self.file_path) if self.file_path else None
        }
