import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Please set GROQ_API_KEY environment variable")
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def generate_response(
        self,
        user_text: str,
        context: Optional[str],
        language: str = "fr",
        intent: Optional[str] = None,
    ) -> str:
        """
        RAG-aware LLM call.
        The assistant MUST answer using provided context when available,
        but also use the detected intent as a hint for style or focus.
        """

        context = context.strip() if context else "Aucun contexte fourni"
        use_context = "Oui" if context else "Non"
        intent_hint = intent or "Aucun"

        prompt = f"""
    Vous êtes un assistant vocal professionnel pour l'assurance.

    Instructions:
    - Si vous avez un contexte fourni, répondez en utilisant ce contexte.
    - Si le contexte est insuffisant, répondez en utilisant vos connaissances générales sur l'assurance.
    - Utilisez le type d'intention détecté pour guider votre réponse: {intent_hint}.
    - Réponse concise : 1 à 2 phrases maximum.
    - Pas d'exemples, pas d'explications, restez sur le sujet.

    Contexte disponible ? {use_context}
    Contexte:
    {context}

    Question de l'utilisateur:
    "{user_text}"

    Réponse:
    """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Assistant RAG pour assurance."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 150,
            "temperature": 0.0,
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
        except Exception as e:
            print(f"LLM call failed: {e}")
            return "Je suis désolé, je n'ai pas pu générer de réponse."

        sentences = text.split(".")
        text = ".".join(sentences[:3]).strip()
        if not text.endswith("."):
            text += "."
        return text
