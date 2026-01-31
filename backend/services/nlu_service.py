import os
import re
import requests
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv
from backend.models.intent import Intent

load_dotenv()


class NLUService:
    # Base confidence levels (can be adjusted by actual model confidence)
    INTENT_BASE_CONFIDENCE = {
        "GREETING": 0.9,
        "GOODBYE": 0.9,
        "CLAIM": 0.75,
        "PAYMENT": 0.75,
        "COVERAGE": 0.75,
        "PROBLEM": 0.6,
        "INQUIRY": 0.6,
        "UNKNOWN": 0.2,
    }

    INTENT_DEFINITIONS = {
        "GREETING": "Salutations initiales, bonjour, hello, débuter une conversation",
        "GOODBYE": "Fin de conversation, au revoir, merci et raccrocher",
        "CLAIM": "Déclarer un sinistre, accident, dégât, demande d'indemnisation, réclamation",
        "PAYMENT": "Questions sur paiement, facture, cotisation, primes, montants dus",
        "COVERAGE": "Questions sur couverture, garanties, ce qui est assuré, limites de police",
        "PROBLEM": "Problème technique, difficulté, insatisfaction, plainte service",
        "INQUIRY": "Question générale, demande d'information, renseignement général",
        "UNKNOWN": "Message non clair, hors contexte, ou incompréhensible",
    }

    PATTERN_RULES = {
        "GREETING": [
            r"\b(bonjour|salut|bonsoir|hello|coucou|hey)\b",
            r"^(bonjour|salut|hello)",
        ],
        "GOODBYE": [
            r"\b(au revoir|bye|adieu|merci bye|à bientôt|bonne journée)\b",
            r"\b(merci|merci beaucoup)\s+(au revoir|bye)",
        ],
        "CLAIM": [
            r"\b(sinistre|accident|dégât|déclar|réclamation|indemnisation)\b",
            r"\b(volé|cassé|endommagé|détruit|brûlé)\b",
        ],
        "PAYMENT": [
            r"\b(payer|payé|paiement|facture|cotisation|prime|montant|coût)\b",
            r"\b(combien|quel prix|tarif)\b",
        ],
        "COVERAGE": [
            r"\b(couvert|couverture|garanti|assuré|protection|inclus)\b",
            r"\b(est-ce que.*couvert|suis-je.*assuré)\b",
        ],
    }

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Please set GROQ_API_KEY environment variable")
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.intent_labels = list(self.INTENT_BASE_CONFIDENCE.keys())

    def _check_pattern_rules(self, text: str) -> Optional[Intent]:
        """Fast-path: Check regex patterns before API call."""
        text_lower = text.lower().strip()

        for intent_name, patterns in self.PATTERN_RULES.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    confidence = self.INTENT_BASE_CONFIDENCE[intent_name]
                    return Intent(name=intent_name, confidence=confidence)

        return None

    @lru_cache(maxsize=1000)
    def _classify_with_llm(self, text: str) -> Intent:
        """LLM-based classification with caching."""
        intent_descriptions = "\n".join(
            [f"- {name}: {desc}" for name, desc in self.INTENT_DEFINITIONS.items()]
        )

        prompt = f"""Classify this customer service message into ONE intent.

AVAILABLE INTENTS:
{intent_descriptions}

CLASSIFICATION RULES:
1. Choose the MOST SPECIFIC intent that fits
2. GREETING and GOODBYE take priority for conversation boundaries
3. If message contains multiple topics, choose the PRIMARY intent
4. Use INQUIRY only if no other intent fits
5. Use UNKNOWN only if message is unclear or nonsensical

MESSAGE: "{text}"

Respond in this EXACT format:
INTENT: [intent name]
CONFIDENCE: [0.0-1.0]
REASONING: [one sentence why]"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert intent classifier for French insurance customer service. Be precise and confident.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 50,
            "temperature": 0.0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.endpoint, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            predicted_intent = "UNKNOWN"
            llm_confidence = 0.5

            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("INTENT:"):
                    predicted_intent = line.split(":", 1)[1].strip().upper()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        llm_confidence = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        llm_confidence = 0.5

            if predicted_intent not in self.intent_labels:
                predicted_intent = "UNKNOWN"
                llm_confidence = 0.2

            base_confidence = self.INTENT_BASE_CONFIDENCE[predicted_intent]
            final_confidence = (llm_confidence * 0.6) + (base_confidence * 0.4)

            return Intent(name=predicted_intent, confidence=round(final_confidence, 2))

        except requests.exceptions.Timeout:
            print("[NLU] API timeout - falling back to UNKNOWN")
            return Intent(name="UNKNOWN", confidence=0.2)

        except requests.exceptions.RequestException as e:
            print(f"[NLU] API error: {e}")
            return Intent(name="UNKNOWN", confidence=0.2)

        except Exception as e:
            print(f"[NLU] Unexpected error: {e}")
            return Intent(name="UNKNOWN", confidence=0.2)

    def detect_intent(self, text: str) -> Intent:
        """
        Detect user intent with hybrid approach: patterns first, then LLM.

        Returns:
            Intent(name: str, confidence: float)
        """
        text = text.strip()

        if not text:
            return Intent(name="UNKNOWN", confidence=0.2)

        if len(text) < 3:
            return Intent(name="UNKNOWN", confidence=0.3)

        pattern_result = self._check_pattern_rules(text)
        if pattern_result:
            print(
                f"[NLU] Pattern match: {pattern_result.name} ({pattern_result.confidence})"
            )
            return pattern_result

        print(f"[NLU] LLM classification for: '{text[:50]}...'")
        return self._classify_with_llm(text)

    def detect_intent_batch(self, texts: list[str]) -> list[Intent]:
        """Batch classification for efficiency."""
        return [self.detect_intent(text) for text in texts]

    def get_intent_stats(self) -> dict:
        """Get cache statistics for monitoring."""
        cache_info = self._classify_with_llm.cache_info()
        return {
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "cache_hit_rate": (
                cache_info.hits / (cache_info.hits + cache_info.misses)
                if (cache_info.hits + cache_info.misses) > 0
                else 0.0
            ),
        }
