import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    INTENT_GUIDELINES = {
        "GREETING": "Réponse chaleureuse et professionnelle. Demandez comment vous pouvez aider.",
        "GOODBYE": "Remerciez le client et souhaitez une bonne journée.",
        "CLAIM": "Ton empathique et rassurant. Guidez sur le processus sans donner de détails spécifiques au contrat.",
        "PAYMENT": "Informations générales sur les paiements. Escaladez seulement pour des modifications de paiement.",
        "COVERAGE": "Expliquez les types de couverture en général. Escaladez seulement pour des détails de contrat spécifique.",
        "PROBLEM": "Montrez de l'empathie, proposez des solutions. Escaladez seulement si problème technique complexe.",
        "INQUIRY": "Réponse informative et utile. Vous pouvez répondre à la plupart des questions générales.",
    }

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Please set GROQ_API_KEY environment variable")
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def _build_system_prompt(self) -> str:
        """Build system prompt that encourages AI handling."""
        return """Vous êtes un assistant vocal IA pour une compagnie d'assurance française. Votre rôle est de GÉRER LA PLUPART DES APPELS vous-même.

VOTRE OBJECTIF: Aider le maximum de clients sans escalader.

CE QUE VOUS POUVEZ FAIRE (gérez ces cas vous-même):
✓ Répondre aux questions générales sur l'assurance
✓ Expliquer les types de couverture (habitation, auto, santé, vie, etc.)
✓ Guider sur les processus (comment déclarer un sinistre, faire un paiement, etc.)
✓ Donner des informations sur les produits standards
✓ Rassurer et montrer de l'empathie
✓ Répondre aux questions sur les profils clients (étudiant, senior, famille, etc.)
✓ Expliquer les documents nécessaires
✓ Clarifier les termes d'assurance

ESCALADEZ UNIQUEMENT SI:
✗ Client demande EXPLICITEMENT un agent humain
✗ Modification de contrat IMMÉDIATE requise
✗ Réclamation complexe avec montants SPÉCIFIQUES à approuver
✗ Litige juridique en COURS
✗ Accès aux données personnelles du dossier REQUIS

RÈGLES:
- Soyez confiant dans vos réponses générales
- Ne dites PAS "Je vais vous transférer" pour des questions simples
- Maximum 2-3 phrases, naturel et conversationnel
- Si vous ne connaissez pas UN détail, donnez l'info générale que vous connaissez
- Utilisez "Un agent pourra vous donner les détails de VOTRE contrat spécifique" seulement si vraiment nécessaire"""

    def _build_user_prompt(
        self,
        user_text: str,
        context: str,
        intent: str,
    ) -> str:
        """Build user prompt with context and intent guidance."""
        intent_guideline = self.INTENT_GUIDELINES.get(
            intent, "Réponse professionnelle et utile."
        )

        has_context = (
            context and context != "Aucun contexte fourni" and len(context) > 10
        )

        if has_context:
            prompt = f"""HISTORIQUE DE CONVERSATION:
{context}

INTENTION: {intent}
APPROCHE: {intent_guideline}

QUESTION ACTUELLE: "{user_text}"

Répondez de manière utile en utilisant l'historique. NE transférez PAS sauf si absolument nécessaire.

RÉPONSE (2-3 phrases max):"""
        else:
            prompt = f"""INTENTION: {intent}
APPROCHE: {intent_guideline}

QUESTION: "{user_text}"

Répondez de manière informative et utile. C'est une question générale que vous POUVEZ gérer.

RÉPONSE (2-3 phrases max):"""

        return prompt

    def generate_response(
        self,
        user_text: str,
        context: Optional[str],
        language: str = "fr",
        intent: Optional[str] = None,
    ) -> str:
        """
        Generate contextual response with intent-aware behavior.
        """
        context = context.strip() if context else ""
        intent = intent or "INQUIRY"

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_text, context, intent)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 150,
            "temperature": 0.3,
            "top_p": 0.9,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.endpoint, json=payload, headers=headers, timeout=15
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            print("[LLM] Request timeout")
            return self._get_fallback_response(intent)
        except requests.exceptions.RequestException as e:
            print(f"[LLM] API error: {e}")
            return self._get_fallback_response(intent)
        except Exception as e:
            print(f"[LLM] Unexpected error: {e}")
            return self._get_fallback_response(intent)

        text = self._clean_response(text)

        if self._contains_dangerous_advice(text):
            print(f"[LLM] Blocked dangerous advice: {text}")
            return "Pour cette question spécifique, un agent pourra mieux vous aider."

        return text

    def _clean_response(self, text: str) -> str:
        """Clean and limit response length."""
        text = text.replace("**", "").replace("*", "").strip()

        prefixes_to_remove = [
            "En tant qu'assistant IA, ",
            "Je suis désolé, mais ",
            "Malheureusement, ",
        ]
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix) :]

        sentences = []
        for sentence in text.split("."):
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
            if len(sentences) >= 3:
                break

        result = ". ".join(sentences).strip()
        if result and not result.endswith((".", "!", "?")):
            result += "."

        return result

    def _contains_dangerous_advice(self, text: str) -> bool:
        """
        Check ONLY for truly dangerous advice - be permissive otherwise.
        """
        text_lower = text.lower()

        dangerous_phrases = [
            "vous devriez prendre ce médicament",
            "je vous garantis que",
            "votre contrat couvre exactement",
            "le montant sera de",
            "vous êtes légalement obligé",
            "je peux approuver",
            "je vais modifier votre",
        ]

        return any(phrase in text_lower for phrase in dangerous_phrases)

    def _get_fallback_response(self, intent: str) -> str:
        """Intent-specific fallback responses when API fails."""
        fallbacks = {
            "GREETING": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
            "GOODBYE": "Au revoir et merci de votre appel !",
            "CLAIM": "Pour déclarer un sinistre, je peux vous guider sur le processus général. Qu'est-il arrivé ?",
            "PAYMENT": "Pour les questions de paiement, je peux vous expliquer les options disponibles.",
            "COVERAGE": "Je peux vous renseigner sur nos différents types de couverture. Que souhaitez-vous savoir ?",
            "PROBLEM": "Je comprends. Pouvez-vous m'expliquer le problème que vous rencontrez ?",
            "INQUIRY": "Je suis là pour répondre à vos questions. Que souhaitez-vous savoir ?",
        }

        return fallbacks.get(
            intent,
            "Je suis à votre écoute. Comment puis-je vous aider ?",
        )
