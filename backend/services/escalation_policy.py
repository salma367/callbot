# backend/services/escalation_policy.py
import os
import requests
from functools import lru_cache
import hashlib
from dotenv import load_dotenv

load_dotenv()


class EscalationPolicy:
    def __init__(
        self,
        confidence_limit: float = 0.3,
        sensitive_intents: list[str] = None,
        max_ambiguity: int = 3,
        use_ai_validation: bool = True,  # Feature flag for AI validation
    ):
        self.confidence_limit = confidence_limit
        self.max_ambiguity = max_ambiguity
        self.use_ai_validation = use_ai_validation
        self.sensitive_intents = sensitive_intents or [
            "CLAIM",
            "LEGAL_ISSUE",
            "CONTRACT_CANCELLATION",
        ]

        # Explicit escalation phrases (high precision)
        self.explicit_agent_requests = [
            "je veux parler à un agent",
            "passez-moi un humain",
            "je veux un représentant",
            "transférez-moi",
            "appelez un agent",
            "parler à quelqu'un",
        ]

        # Question patterns that indicate inquiry, not emergency
        self.question_patterns = [
            "est-ce qu'",
            "est-il possible",
            "peut-on",
            "comment",
            "quand",
            "pourquoi",
            "quelle est",
            "quel est",
            "puis-je",
            "dois-je",
        ]

        # Critical keywords that need AI validation
        self.critical_keywords = [
            # life-threatening (tier 1 - highest priority)
            "tué",
            "meurtre",
            "sang",
            "urgence vitale",
            "risque vital",
            "mourir",
            # severe injury (tier 2)
            "blessé gravement",
            "accident grave",
            "brûlure grave",
            "explosion",
            # violence/crime (tier 2)
            "agression",
            "kidnapping",
            "braquage",
            "attaque armée",
            "terrorisme",
        ]

        # Lower-priority keywords (likely false positives without context)
        self.context_dependent_keywords = [
            "blessé",
            "accident",
            "violence",
            "vol",
            "criminel",
            "infection",
            "fracture",
            "avocat",
            "litige",
            "confidentiel",
            "arme",
            "menace",
        ]

        # Initialize AI service if enabled
        if self.use_ai_validation:
            self.api_key = os.getenv("GROQ_API_KEY")
            if self.api_key:
                self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
                self.model = "llama-3.3-70b-versatile"
            else:
                print("[WARN] GROQ_API_KEY not found. AI validation disabled.")
                self.use_ai_validation = False

    def _is_question_context(self, text: str) -> bool:
        """Quick check if message is a question (likely not an emergency)."""
        text_lower = text.lower().strip()

        # Check for question patterns at start
        if any(text_lower.startswith(pattern) for pattern in self.question_patterns):
            return True

        # Check for question words anywhere + question mark
        if "?" in text and any(
            pattern in text_lower for pattern in self.question_patterns
        ):
            return True

        return False

    def _contains_explicit_agent_request(self, text: str) -> bool:
        """Check for explicit agent escalation requests."""
        text_lower = text.lower().strip()
        return any(phrase in text_lower for phrase in self.explicit_agent_requests)

    @lru_cache(maxsize=500)
    def _analyze_severity_cached(self, text_hash: str, user_text: str) -> dict:
        """Cached AI-based severity analysis to avoid redundant API calls."""
        return self._analyze_severity(user_text)

    def _analyze_severity(self, user_text: str) -> dict:
        """
        AI validation for ambiguous cases.
        Returns: {"requires_escalation": bool, "reason": str, "confidence": float}
        """
        if not self.use_ai_validation:
            return {
                "requires_escalation": False,
                "reason": "ai_disabled",
                "confidence": 0.0,
            }

        prompt = f"""Analyze if this customer message requires IMMEDIATE human agent escalation.

Escalate ONLY if:
1. Describing an ACTUAL ongoing emergency/injury (not past/resolved/hypothetical)
2. Explicit DEMAND to speak with human agent
3. Active crime/violence situation requiring intervention
4. Customer is ALREADY in legal dispute (not asking about procedures)

DO NOT escalate if:
- Hypothetical questions ("what if", "can I", "is it possible")
- Past incidents mentioned casually
- General policy questions
- Asking IF agent contact is possible

Message: "{user_text}"

Respond ONLY in this format (no extra text):
ESCALATE: YES or NO
REASON: brief reason
CONFIDENCE: 0.0-1.0"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You minimize false positives. Be conservative with escalation.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 80,
            "temperature": 0.0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.endpoint, json=payload, headers=headers, timeout=8
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Parse response
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            escalate = False
            reason = "unknown"
            confidence = 0.5

            for line in lines:
                if line.startswith("ESCALATE:"):
                    escalate = "YES" in line.upper()
                elif line.startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        confidence = 0.5

            return {
                "requires_escalation": escalate,
                "reason": reason,
                "confidence": confidence,
            }

        except Exception as e:
            print(f"[ESCALATION] AI analysis failed: {e}")
            # Conservative fallback: don't escalate on error
            return {
                "requires_escalation": False,
                "reason": "ai_error",
                "confidence": 0.0,
            }

    def should_escalate(
        self,
        global_confidence: float,
        intent_name: str,
        ambiguity_count: int = 0,
        user_text: str = "",
    ) -> tuple[str, str]:
        """
        Multi-tier escalation logic with AI validation.
        Returns: (decision: str, reason: str)
        """
        text_lower = user_text.lower().strip()

        # ═══════════════════════════════════════════════════════════
        # TIER 1: EXPLICIT AGENT REQUESTS (no AI needed)
        # ═══════════════════════════════════════════════════════════
        if self._contains_explicit_agent_request(text_lower):
            return "ESCALATE", "USER_REQUEST_AGENT"

        # ═══════════════════════════════════════════════════════════
        # TIER 2: CRITICAL KEYWORDS (AI validation required)
        # ═══════════════════════════════════════════════════════════
        has_critical_keyword = any(
            word in text_lower for word in self.critical_keywords
        )

        if has_critical_keyword:
            # Skip AI if it's clearly a question
            if self._is_question_context(user_text):
                # Question about critical topic, but not an emergency
                pass  # Continue to standard logic
            else:
                # Use AI to validate if this is a real emergency
                text_hash = hashlib.md5(user_text.encode()).hexdigest()
                severity = self._analyze_severity_cached(text_hash, user_text)

                if severity["requires_escalation"] and severity["confidence"] > 0.7:
                    return "ESCALATE", f"CRITICAL_SITUATION: {severity['reason']}"

        # ═══════════════════════════════════════════════════════════
        # TIER 3: CONTEXT-DEPENDENT KEYWORDS (AI validation if not question)
        # ═══════════════════════════════════════════════════════════
        has_context_keyword = any(
            word in text_lower for word in self.context_dependent_keywords
        )

        if has_context_keyword and not self._is_question_context(user_text):
            # Might be serious, validate with AI
            text_hash = hashlib.md5(user_text.encode()).hexdigest()
            severity = self._analyze_severity_cached(text_hash, user_text)

            if severity["requires_escalation"] and severity["confidence"] > 0.75:
                return "ESCALATE", f"SENSITIVE_CONTENT: {severity['reason']}"

        # ═══════════════════════════════════════════════════════════
        # TIER 4: LOW CONFIDENCE HANDLING
        # ═══════════════════════════════════════════════════════════
        if global_confidence < self.confidence_limit:
            if ambiguity_count >= self.max_ambiguity:
                return "ESCALATE", "REPEATED_AMBIGUITY"
            else:
                return "ASK_CLARIFICATION", "LOW_CONFIDENCE"

        # ═══════════════════════════════════════════════════════════
        # TIER 5: SENSITIVE INTENTS (with AI validation)
        # ═══════════════════════════════════════════════════════════
        if intent_name.upper() in self.sensitive_intents:
            # For sensitive intents, check if there's concerning content
            if has_critical_keyword or has_context_keyword:
                if not self._is_question_context(user_text):
                    text_hash = hashlib.md5(user_text.encode()).hexdigest()
                    severity = self._analyze_severity_cached(text_hash, user_text)

                    if severity["requires_escalation"] and severity["confidence"] > 0.6:
                        return "ESCALATE", f"SENSITIVE_INTENT: {intent_name}"

        # ═══════════════════════════════════════════════════════════
        # DEFAULT: AI CAN HANDLE
        # ═══════════════════════════════════════════════════════════
        return "AUTO_HANDLED", "AUTO_HANDLED"
