from backend.models import intent
from backend.services.asr_service import ASRService
from backend.services.tts_service import TTSService
from backend.services.nlu_service import NLUService
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService


class VoicePipeline:
    MIN_CONFIDENCE = 0.35

    def __init__(self):
        self.asr = ASRService()
        self.tts = TTSService()
        self.nlu = NLUService()
        self.llm = LLMService()
        self.rag = RAGService()

    def process_audio(self, audio_path: str) -> dict:
        print("🔹 Starting voice pipeline...")
        print(f"Audio file: {audio_path}")

        # ------------------
        # 1️⃣ ASR
        # ------------------
        asr_result = self.asr.transcribe_voice(audio_path)
        text = asr_result.get("text", "").strip()
        language = asr_result.get("language", "unknown")
        confidence = asr_result.get("confidence", 0.0)

        print(
            f"ASR Result: text='{text}', language={language}, confidence={confidence}"
        )

        if not text or confidence < self.MIN_CONFIDENCE:
            print("⚠️ ASR failed or confidence too low.")
            return {
                "error": "asr_failed",
                "language": language,
                "confidence": confidence,
            }

        # ------------------
        # 2️⃣ NLU
        # ------------------
        detected_intent = self.nlu.detect_intent(text)
        print(f"Detected intent: {detected_intent.name}")

        # ------------------
        # 3️⃣ RAG retrieval
        # ------------------
        contexts = self.rag.retrieve(text, k=4)
        print(f"Retrieved chunks ({len(contexts)}):")
        for i, c in enumerate(contexts, 1):
            print(f"Chunk {i}: {c[:100]}...")

        context = "\n".join(contexts) if contexts else ""
        if not context:
            print("⚠️ No relevant context found from RAG. Passing empty context to LLM.")

        # ------------------
        # 4️⃣ LLM
        # ------------------
        try:
            response_text = self.llm.generate_response(
                user_text=text,
                context=context,
                language=language,
                intent=detected_intent.name if detected_intent else None,
            )
            print(f"LLM Response: {response_text}")
        except Exception as e:
            print(f"❌ LLM failed: {e}")
            response_text = "Je suis désolé, je n'ai pas pu générer de réponse."

        # ------------------
        # 5️⃣ TTS
        # ------------------
        try:
            tts_audio_path = self.tts.synthesize(
                text=response_text,
                lang="fr",
            )
            print(f"TTS Audio Path: {tts_audio_path}")
        except Exception as e:
            print(f"❌ TTS failed: {e}")
            tts_audio_path = None

        # ------------------
        # 6️⃣ Return full response
        # ------------------
        return {
            "text": text,
            "intent": detected_intent.name if detected_intent else None,
            "response_text": response_text,
            "language": language,
            "confidence": confidence,
            "audio_response": tts_audio_path,
        }
