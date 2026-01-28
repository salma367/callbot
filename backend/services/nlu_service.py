import os
import requests
from typing import Optional
from dotenv import load_dotenv
from backend.models.intent import Intent

load_dotenv()


class NLUService:
    """
    NLU Service responsible ONLY for intent detection.
    Confidence is derived deterministically (no hallucinated scores).
    """

    INTENT_CONFIDENCE_MAP = {
        "GREETING": 0.9,
        "GOODBYE": 0.9,
        "CLAIM": 0.75,
        "PAYMENT": 0.75,
        "COVERAGE": 0.75,
        "PROBLEM": 0.6,
        "INQUIRY": 0.6,
        "UNKNOWN": 0.2,
    }

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Please set GROQ_API_KEY environment variable")

        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

        self.intent_labels = list(self.INTENT_CONFIDENCE_MAP.keys())

    def detect_intent(self, text: str) -> Intent:
        """
        Uses Groq API to classify the intent of a user utterance.

        Returns:
            Intent(name: str, confidence: float)
        """

        text = text.strip()
        if not text:
            return Intent(name="UNKNOWN", confidence=0.2)

        prompt = f"""
Classify the following user message into ONE of these intents:
{', '.join(self.intent_labels)}.

Respond with ONLY the intent name, no explanation.

Message:
"{text}"
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an intent classification AI."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 10,
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
            predicted_intent = data["choices"][0]["message"]["content"].strip().upper()
        except Exception:
            predicted_intent = "UNKNOWN"

        if predicted_intent not in self.intent_labels:
            predicted_intent = "UNKNOWN"

        confidence = self.INTENT_CONFIDENCE_MAP.get(predicted_intent, 0.5)

        return Intent(name=predicted_intent, confidence=confidence)
