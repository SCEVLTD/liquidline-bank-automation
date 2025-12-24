"""
Liquidline Bank Reconciliation Automation
Layer 4: AI Inference Matcher

Uses LLM API for intelligent matching of ambiguous transactions
that couldn't be matched by earlier layers.

Supports:
- OpenRouter (recommended - access to multiple models)
- Anthropic API (direct)

Coverage: ~22% of transactions (fallback layer)
Accuracy: ~70%
"""

import os
import json
from typing import List, Optional
import logging

from ..models.transaction import (
    Transaction, MatchResult, ConfidenceLevel, MatchMethod
)

logger = logging.getLogger(__name__)


class AIMatcher:
    """
    Layer 4 Matcher: AI Inference

    Uses LLM to intelligently analyze transaction details
    and suggest customer matches based on contextual understanding.

    Supports OpenRouter (recommended) or direct Anthropic API.
    """

    SYSTEM_PROMPT = """You are an expert financial analyst assistant helping to match bank transactions to customers.

You will be given:
1. A bank transaction with reference and detail fields
2. A list of potential customer matches with their codes and names

Your task is to:
1. Analyze the transaction reference and details
2. Identify which customer is most likely the correct match
3. Provide a confidence score (0.0 to 1.0)
4. Explain your reasoning

Respond in JSON format:
{
    "matched_customer_code": "CODE123" or null if no match,
    "matched_customer_name": "Customer Name" or null,
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of why this match was selected",
    "alternative_matches": [
        {"code": "CODE456", "name": "Alternative Customer", "confidence": 0.5}
    ]
}

Important:
- Only match if you're reasonably confident (>0.5)
- Consider partial name matches, abbreviations, and common variations
- If truly ambiguous, return null match with explanation
- Bank references often contain customer names, invoice numbers, or account codes"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openrouter",  # "openrouter" or "anthropic"
        model: Optional[str] = None
    ):
        """
        Args:
            api_key: API key. If None, will try to load from env.
            provider: "openrouter" or "anthropic"
            model: Model to use. Defaults based on provider.
        """
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = None

        # Set default models
        if not self.model:
            if self.provider == "openrouter":
                self.model = "anthropic/claude-3.5-sonnet"  # OpenRouter model name
            else:
                self.model = "claude-3-5-sonnet-20241022"

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the API client"""
        if not self.api_key:
            logger.warning("No API key found. Layer 4 AI matching disabled.")
            logger.info("Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY environment variable.")
            return

        try:
            if self.provider == "openrouter":
                self._initialize_openrouter()
            else:
                self._initialize_anthropic()
        except Exception as e:
            logger.warning(f"Failed to initialize AI client: {e}")
            self.client = None

    def _initialize_openrouter(self):
        """Initialize OpenRouter client (OpenAI-compatible)"""
        try:
            from openai import OpenAI

            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://brandedai.net",
                    "X-Title": "Liquidline Bank Automation"
                }
            )
            logger.info(f"OpenRouter client initialized (model: {self.model})")

        except ImportError:
            logger.warning("openai package not installed. Run: pip install openai")
            self.client = None

    def _initialize_anthropic(self):
        """Initialize direct Anthropic client"""
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Anthropic client initialized (model: {self.model})")

        except ImportError:
            logger.warning("anthropic package not installed. Run: pip install anthropic")
            self.client = None

    def match(
        self,
        transaction: Transaction,
        candidate_customers: List[dict]
    ) -> Optional[MatchResult]:
        """
        Attempt to match transaction using AI

        Args:
            transaction: Transaction to match
            candidate_customers: List of potential customer matches
                                Each dict should have: code, name

        Returns:
            MatchResult if AI suggests a match, None otherwise
        """
        if not self.client:
            return None

        if not candidate_customers:
            logger.debug("No candidate customers provided for AI matching")
            return None

        try:
            user_prompt = self._build_prompt(transaction, candidate_customers)

            if self.provider == "openrouter":
                response_text = self._call_openrouter(user_prompt)
            else:
                response_text = self._call_anthropic(user_prompt)

            if response_text:
                return self._parse_response(response_text, candidate_customers)

        except Exception as e:
            logger.error(f"AI matching failed: {e}")

        return None

    def _call_openrouter(self, user_prompt: str) -> Optional[str]:
        """Call OpenRouter API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return None

    def _call_anthropic(self, user_prompt: str) -> Optional[str]:
        """Call Anthropic API directly"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None

    def _build_prompt(self, transaction: Transaction, candidates: List[dict]) -> str:
        """Build the user prompt"""
        candidates_text = "\n".join([
            f"- Code: {c.get('code', 'N/A')}, Name: {c.get('name', 'N/A')}"
            for c in candidates[:20]
        ])

        return f"""Analyze this bank transaction and identify the best customer match:

TRANSACTION:
- Date: {transaction.post_date.strftime('%d/%m/%Y')}
- Amount: £{transaction.amount:,.2f}
- Customer Reference: {transaction.customer_reference or 'N/A'}
- Transaction Detail: {transaction.transaction_detail or 'N/A'}
- Type: {transaction.transaction_type}

POTENTIAL CUSTOMER MATCHES:
{candidates_text}

Which customer is this transaction most likely from? Respond in JSON format."""

    def _parse_response(self, response_text: str, candidates: List[dict]) -> Optional[MatchResult]:
        """Parse AI JSON response into a MatchResult"""
        try:
            # Extract JSON from response (handle various formats)
            json_str = self._extract_json(response_text)
            if not json_str:
                logger.error("Could not extract JSON from AI response")
                return None

            result = json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return None

        # Process the parsed JSON result
        if not result.get("matched_customer_code"):
            logger.debug(f"AI found no match: {result.get('reasoning', 'No reason provided')}")
            return None

        confidence = float(result.get("confidence", 0.5))

        if confidence >= 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        alternatives = []
        for alt in result.get("alternative_matches", []):
            if alt.get("code"):
                alternatives.append({
                    "customer_code": alt["code"],
                    "customer_name": alt.get("name", ""),
                    "score": alt.get("confidence", 0.5)
                })

        return MatchResult(
            customer_code=result["matched_customer_code"],
            customer_name=result.get("matched_customer_name", ""),
            confidence_score=confidence,
            confidence_level=confidence_level,
            match_method=MatchMethod.LAYER_4_AI_INFERENCE,
            invoice_allocations=[],
            match_details=f"AI inference: {result.get('reasoning', 'No explanation provided')}",
            alternative_matches=alternatives
        )

    def _extract_json(self, response_text: str) -> Optional[str]:
        """
        Extract JSON object from AI response text.
        Handles markdown code blocks, extra text, and various formats.
        """
        if not response_text:
            return None

        text = response_text.strip()

        # Method 1: Extract from markdown code blocks
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0].strip()
                # Validate it's valid JSON
                json.loads(json_str)
                return json_str
            except (IndexError, json.JSONDecodeError):
                pass

        if "```" in text:
            try:
                json_str = text.split("```")[1].split("```")[0].strip()
                json.loads(json_str)
                return json_str
            except (IndexError, json.JSONDecodeError):
                pass

        # Method 2: Find JSON object using brace matching
        start_idx = text.find('{')
        if start_idx != -1:
            brace_count = 0
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[start_idx:i+1]
                        try:
                            json.loads(json_str)
                            return json_str
                        except json.JSONDecodeError:
                            pass
                        break

        # Method 3: Try the whole text as JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        return None

    def get_stats(self) -> dict:
        """Get matcher statistics"""
        return {
            "layer": 4,
            "name": "AI Inference",
            "provider": self.provider,
            "model": self.model,
            "available": self.client is not None
        }
